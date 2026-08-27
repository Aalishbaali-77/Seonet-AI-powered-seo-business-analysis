from __future__ import annotations

from django.utils import timezone

from apps.audits.analysis import analyze_crawl
from apps.audits.engine import crawl_website, plan_limits
from apps.audits.models import Audit
from apps.auditlog.services import write_audit
from apps.billing.entitlements import tenant_module_codes
from apps.common.exceptions import APIError
from apps.crawler.ssrf import SSRFBlocked
from apps.jobs import services as job_services
from apps.jobs.models import Job
from apps.usage.services import record_usage
from apps.websites.models import Website


def assert_can_start_audit(tenant) -> None:
    if "audits" not in tenant_module_codes(tenant) and "websites" not in tenant_module_codes(tenant):
        raise APIError("Website intelligence is not included in the current package.", code="FEATURE_DISABLED", status_code=403)
    _, max_audits = plan_limits(tenant)
    period_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    used = (
        Audit.objects.for_tenant(tenant)
        .filter(created_at__gte=period_start)
        .exclude(status=Audit.Status.FAILED)
        .count()
    )
    if used >= max_audits:
        raise APIError(
            "This workspace has used its monthly audit allowance. Upgrade the package to run more audits.",
            code="QUOTA_EXCEEDED",
            status_code=402,
        )


def start_audit(*, website: Website, user) -> Job:
    assert_can_start_audit(website.tenant)
    job = job_services.create_job(
        tenant=website.tenant,
        user=user,
        job_type="run_audit",
        payload={"website_id": str(website.id), "url": website.url},
    )
    audit = Audit.objects.create(
        tenant=website.tenant,
        website=website,
        job=job,
        status=Audit.Status.PENDING,
    )
    write_audit(
        action="AUDIT_STARTED",
        user=user,
        tenant=website.tenant,
        resource_type="audit",
        resource_id=audit.id,
        metadata={"website_id": str(website.id)},
    )
    job.result = {"stage": "Queued"}
    job.save(update_fields=["result", "updated_at"])
    job.celery_task_id = _enqueue_audit_job(str(job.id))
    job.save(update_fields=["celery_task_id", "updated_at"])
    return job


def _enqueue_audit_job(job_id: str) -> str:
    from threading import Thread

    from django.conf import settings
    from django.db import connections, transaction

    from workers.tasks import run_website_audit

    eager = getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False)
    propagate = getattr(settings, "CELERY_TASK_EAGER_PROPAGATES", False)
    if eager and not propagate:
        def runner() -> None:
            connections.close_all()
            run_website_audit(job_id)

        transaction.on_commit(lambda: Thread(target=runner, daemon=True, name=f"sipulse-audit-{job_id}").start())
        return ""
    async_result = run_website_audit.delay(job_id)
    return async_result.id or ""


def execute_audit_job(job: Job) -> Audit:
    website_id = job.payload.get("website_id")
    website = Website.objects.for_tenant(job.tenant).get(id=website_id)
    audit = Audit.objects.filter(job=job).first()
    if audit is None:
        audit = Audit.objects.create(tenant=job.tenant, website=website, job=job, status=Audit.Status.RUNNING)
    try:
        job_services.mark_running(job, progress=5, result={"stage": "Preparing audit", "website_validated": True})
        audit.status = Audit.Status.RUNNING
        audit.save(update_fields=["status", "updated_at"])
        job_services.mark_progress(job, progress=20, result={"stage": "Crawling"})
        crawl = crawl_website(website, job=job)
        audit.crawl = crawl
        audit.save(update_fields=["crawl", "updated_at"])
        job_services.mark_progress(
            job,
            progress=56,
            result={"stage": "Measuring performance", "pages_discovered": crawl.pages_discovered},
        )
        from apps.audits.browser_ux import attach_browser_ux

        attach_browser_ux(crawl)
        job_services.mark_progress(
            job,
            progress=62,
            result={"stage": "Technical analysis", "pages_discovered": crawl.pages_discovered},
        )
        record_usage(
            tenant=job.tenant,
            user=job.user,
            event_type="website_page_crawled",
            quantity=crawl.pages_discovered,
            metadata={"website_id": str(website.id)},
        )
        job_services.mark_progress(job, progress=75, result={"stage": "Content analysis"})
        analyze_crawl(audit, crawl)
        job_services.mark_progress(job, progress=90, result={"stage": "Generating report"})
        record_usage(tenant=job.tenant, user=job.user, event_type="audit_completed", quantity=1, metadata={"audit_id": str(audit.id)})
        job_services.mark_completed(
            job,
            result={
                "stage": "Completed",
                "audit_id": str(audit.id),
                "pages_crawled": audit.pages_crawled,
                "issues": audit.issue_count,
                "overall_score": audit.overall_score,
            },
        )
        write_audit(
            action="AUDIT_COMPLETED",
            user=job.user,
            tenant=job.tenant,
            resource_type="audit",
            resource_id=audit.id,
        )
        from apps.integrations.push import push_audit

        push_audit(job.tenant, audit)
        return audit
    except SSRFBlocked as exc:
        message = str(exc.detail)
        audit.status = Audit.Status.FAILED
        audit.save(update_fields=["status", "updated_at"])
        job_services.mark_failed(job, error=message, result={"stage": "Failed"})
        return audit
    except Exception as exc:
        audit.status = Audit.Status.FAILED
        audit.save(update_fields=["status", "updated_at"])
        job_services.mark_failed(job, error=str(exc)[:4000], result={"stage": "Failed"})
        return audit
