from celery import shared_task


@shared_task(name="workers.ping")
def ping() -> str:
    return "pong"


@shared_task(name="workers.run_website_audit", queue="audit")
def run_website_audit(job_id: str) -> str:
    from apps.jobs.models import Job
    from apps.audits.services import execute_audit_job

    job = Job.objects.select_related("tenant", "user").get(id=job_id)
    execute_audit_job(job)
    return job_id


@shared_task(name="workers.discover_leads", queue="leads")
def discover_leads(job_id: str) -> str:
    from apps.jobs.models import Job
    from apps.leads.services import execute_discovery_job

    job = Job.objects.select_related("tenant", "user").get(id=job_id)
    execute_discovery_job(job)
    return job_id


@shared_task(name="workers.sync_commerce", queue="default")
def sync_commerce(job_id: str) -> str:
    from apps.jobs.models import Job
    from apps.business.sync import execute_store_sync

    job = Job.objects.select_related("tenant", "user").get(id=job_id)
    execute_store_sync(job)
    return job_id


@shared_task(name="workers.import_commerce", queue="default")
def import_commerce(job_id: str) -> str:
    from apps.jobs.models import Job
    from apps.business.imports import execute_csv_import

    job = Job.objects.select_related("tenant", "user").get(id=job_id)
    execute_csv_import(job)
    return job_id


@shared_task(name="workers.import_markets", queue="default")
def import_markets(job_id: str) -> str:
    from apps.jobs.models import Job
    from apps.markets.imports import execute_signal_import

    job = Job.objects.select_related("tenant", "user").get(id=job_id)
    execute_signal_import(job)
    return job_id


@shared_task(name="workers.collect_markets", queue="default")
def collect_markets(job_id: str) -> str:
    from apps.jobs.models import Job
    from apps.markets.collect import execute_market_collect

    job = Job.objects.select_related("tenant", "user").get(id=job_id)
    execute_market_collect(job)
    return job_id


@shared_task(name="workers.analyze_business", queue="default")
def analyze_business(job_id: str) -> str:
    from apps.jobs.models import Job
    from apps.business.analysis import execute_business_analysis

    job = Job.objects.select_related("tenant", "user").get(id=job_id)
    execute_business_analysis(job)
    return job_id


@shared_task(name="workers.analyze_market", queue="default")
def analyze_market(job_id: str) -> str:
    from apps.jobs.models import Job
    from apps.markets.research import execute_market_analysis

    job = Job.objects.select_related("tenant", "user").get(id=job_id)
    execute_market_analysis(job)
    return job_id


@shared_task(name="workers.apply_audit_fixes", queue="audit")
def apply_audit_fixes(job_id: str) -> str:
    from apps.jobs.models import Job
    from apps.websites.fix_jobs import execute_fix_run

    job = Job.objects.select_related("tenant", "user").get(id=job_id)
    execute_fix_run(job)
    return job_id


@shared_task(name="workers.enrich_leads", queue="leads")
def enrich_leads(job_id: str) -> str:
    from apps.jobs.models import Job
    from apps.leads.enrichment import execute_enrich_job

    job = Job.objects.select_related("tenant", "user").get(id=job_id)
    execute_enrich_job(job)
    return job_id


@shared_task(name="workers.check_keyword_ranks", queue="audit")
def check_keyword_ranks(job_id: str) -> str:
    from apps.jobs.models import Job
    from apps.websites.keywords import execute_keyword_rank

    job = Job.objects.select_related("tenant", "user").get(id=job_id)
    execute_keyword_rank(job)
    return job_id
