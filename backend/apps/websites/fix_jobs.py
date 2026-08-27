from __future__ import annotations

from apps.audits.models import Audit
from apps.audits.services import assert_can_start_audit, execute_audit_job
from apps.auditlog.services import write_audit
from apps.common.crypto import decrypt_json
from apps.common.exceptions import APIError
from apps.jobs import services as job_services
from apps.websites.compare import intelligence_compare
from apps.websites.fixes import apply_planned_fixes, plan_fixes
from apps.websites.models import AuditFixRun, WebsiteAccess
from apps.websites.transports import build_transport


def access_transport(access: WebsiteAccess):
    return build_transport(
        kind=access.kind,
        config=access.config or {},
        secrets=decrypt_json(access.secret_blob),
        website_url=access.website.url,
    )


def start_fix_run(*, website, user, audit: Audit) -> "object":
    if audit.website_id != website.id or audit.tenant_id != website.tenant_id:
        raise APIError("The baseline audit does not belong to this website.", code="VALIDATION_ERROR")
    if audit.status != Audit.Status.COMPLETED:
        raise APIError("Finish the first audit before applying recommended fixes.", code="VALIDATION_ERROR")
    access = WebsiteAccess.objects.for_tenant(website.tenant).filter(website=website).first()
    if access is None or access.status != WebsiteAccess.Status.CONNECTED:
        raise APIError("Connect website code access first, then apply recommended fixes.", code="VALIDATION_ERROR")
    assert_can_start_audit(website.tenant)
    transport = access_transport(access)
    plan = plan_fixes(
        website=website,
        audit=audit,
        can_write_files=transport.can_write_files(),
        wordpress=access.kind == WebsiteAccess.Kind.WORDPRESS,
    )
    if not plan.get("applicable"):
        raise APIError(
            "No allowlisted fixes can be applied with this access method. Connect FTP, SFTP, or cPanel for file changes, or keep recommendations as a manual roadmap.",
            code="VALIDATION_ERROR",
        )
    job = job_services.create_job(
        tenant=website.tenant,
        user=user,
        job_type="apply_audit_fixes",
        payload={"website_id": str(website.id), "audit_id": str(audit.id)},
    )
    run = AuditFixRun.objects.create(
        tenant=website.tenant,
        website=website,
        access=access,
        baseline_audit=audit,
        job=job,
        status=AuditFixRun.Status.PENDING,
        plan=plan,
    )
    job.result = {"stage": "Queued", "fix_run_id": str(run.id), "baseline_audit_id": str(audit.id)}
    job.save(update_fields=["result", "updated_at"])
    job.celery_task_id = _enqueue(str(job.id))
    job.save(update_fields=["celery_task_id", "updated_at"])
    job.refresh_from_db()
    return job


def _enqueue(job_id: str) -> str:
    from threading import Thread

    from django.conf import settings
    from django.db import connections, transaction

    from workers.tasks import apply_audit_fixes

    eager = getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False)
    propagate = getattr(settings, "CELERY_TASK_EAGER_PROPAGATES", False)
    if eager and not propagate:
        def runner() -> None:
            connections.close_all()
            apply_audit_fixes(job_id)

        transaction.on_commit(lambda: Thread(target=runner, daemon=True).start())
        return "thread"
    return str(apply_audit_fixes.delay(job_id).id)


def execute_fix_run(job) -> dict:
    run = AuditFixRun.objects.select_related("website", "access", "baseline_audit").filter(job=job).first()
    if run is None:
        job_services.mark_failed(job, error="Fix run was not found.", result={"stage": "Failed"})
        return {}
    website = run.website
    access = run.access
    baseline = run.baseline_audit
    job_services.mark_running(job, progress=8, result={"stage": "Connecting site access", "fix_run_id": str(run.id), "baseline_audit_id": str(baseline.id)})
    run.status = AuditFixRun.Status.APPLYING
    run.save(update_fields=["status", "updated_at"])
    try:
        transport = access_transport(access)
        transport.test()
        job_services.mark_progress(job, progress=28, result={"stage": "Applying recommended fixes", "fix_run_id": str(run.id)})
        applied = apply_planned_fixes(website=website, audit=baseline, transport=transport, plan=run.plan)
        run.result = applied
        run.save(update_fields=["result", "updated_at"])
        if not applied.get("applied"):
            message = (applied.get("errors") or ["No recommended file or WordPress setting could be written."])[0]
            run.status = AuditFixRun.Status.FAILED
            run.error = str(message)[:4000]
            run.save(update_fields=["status", "error", "updated_at"])
            job_services.mark_failed(job, error=str(message)[:4000], result={"stage": "Failed", "fix_run_id": str(run.id), **applied})
            return applied
        job_services.mark_progress(job, progress=58, result={"stage": "Re-checking SEO / AEO / GEO", "fix_run_id": str(run.id), "applied": len(applied.get("applied") or [])})
        run.status = AuditFixRun.Status.REAUDITING
        run.save(update_fields=["status", "updated_at"])
        followup_job = job_services.create_job(
            tenant=website.tenant,
            user=job.user,
            job_type="run_audit",
            payload={"website_id": str(website.id), "url": website.url, "parent_fix_run": str(run.id)},
        )
        followup = Audit.objects.create(tenant=website.tenant, website=website, job=followup_job, status=Audit.Status.PENDING)
        execute_audit_job(followup_job)
        followup.refresh_from_db()
        if followup.status != Audit.Status.COMPLETED:
            raise APIError(followup_job.error or "The follow-up audit failed.", code="VALIDATION_ERROR")
        comparison = intelligence_compare(baseline=baseline, followup=followup)
        run.followup_audit = followup
        run.comparison = comparison
        run.status = AuditFixRun.Status.COMPLETED
        run.save(update_fields=["followup_audit", "comparison", "status", "updated_at"])
        write_audit(
            action="AUDIT_FIXES_APPLIED",
            tenant=website.tenant,
            user=job.user,
            resource_type="website",
            resource_id=website.id,
            metadata={"baseline_audit_id": str(baseline.id), "followup_audit_id": str(followup.id), "applied": len(applied.get("applied") or [])},
        )
        result = {
            "stage": "Completed",
            "fix_run_id": str(run.id),
            "baseline_audit_id": str(baseline.id),
            "followup_audit_id": str(followup.id),
            "applied": len(applied.get("applied") or []),
            "skipped": len(applied.get("skipped") or []),
            "overall_before": baseline.overall_score,
            "overall_after": followup.overall_score,
        }
        job_services.mark_completed(job, result=result)
        return result
    except Exception as exc:  # noqa: BLE001
        run.status = AuditFixRun.Status.FAILED
        run.error = str(exc)[:4000]
        run.save(update_fields=["status", "error", "updated_at"])
        job_services.mark_failed(job, error=str(exc)[:4000], result={"stage": "Failed", "fix_run_id": str(run.id)})
        return {"error": str(exc)[:4000]}
