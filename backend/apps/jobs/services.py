from __future__ import annotations

from django.utils import timezone

from apps.jobs.models import Job


def create_job(*, tenant, user, job_type: str, payload: dict | None = None) -> Job:
    return Job.objects.create(
        tenant=tenant,
        user=user,
        job_type=job_type,
        status=Job.Status.QUEUED,
        payload=payload or {},
        progress=0,
    )


def mark_running(job: Job, *, progress: int = 1, result: dict | None = None) -> Job:
    job.status = Job.Status.RUNNING
    job.progress = progress
    if job.started_at is None:
        job.started_at = timezone.now()
    if result:
        job.result = {**(job.result or {}), **result}
    job.save(update_fields=["status", "progress", "started_at", "result", "updated_at"])
    return job


def mark_progress(job: Job, *, progress: int, result: dict | None = None) -> Job:
    job.progress = min(progress, 99)
    if result:
        job.result = {**(job.result or {}), **result}
    job.save(update_fields=["progress", "result", "updated_at"])
    return job


def mark_completed(job: Job, *, result: dict | None = None) -> Job:
    job.status = Job.Status.COMPLETED
    job.progress = 100
    job.completed_at = timezone.now()
    if result:
        job.result = {**(job.result or {}), **result}
    job.save(update_fields=["status", "progress", "completed_at", "result", "updated_at"])
    return job


def cancel_job(job: Job) -> Job:
    if job.status in {Job.Status.COMPLETED, Job.Status.FAILED, Job.Status.CANCELLED}:
        return job
    job.status = Job.Status.CANCELLED
    job.completed_at = timezone.now()
    job.error = job.error or "Cancelled by a workspace member."
    job.save(update_fields=["status", "completed_at", "error", "updated_at"])
    return job


def mark_failed(job: Job, *, error: str, result: dict | None = None) -> Job:
    job.status = Job.Status.FAILED
    job.error = error[:4000]
    job.completed_at = timezone.now()
    if result:
        job.result = {**(job.result or {}), **result}
    job.save(update_fields=["status", "error", "completed_at", "result", "updated_at"])
    return job
