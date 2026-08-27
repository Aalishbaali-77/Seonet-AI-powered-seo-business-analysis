from __future__ import annotations

from django.db import models

from apps.common.models import TenantOwnedModel


class Job(TenantOwnedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        QUEUED = "QUEUED", "Queued"
        RUNNING = "RUNNING", "Running"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"
        CANCELLED = "CANCELLED", "Cancelled"

    user = models.ForeignKey("users.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="jobs")
    job_type = models.CharField(max_length=80, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    progress = models.PositiveSmallIntegerField(default=0)
    payload = models.JSONField(default=dict, blank=True)
    result = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True)
    retry_count = models.PositiveSmallIntegerField(default=0)
    celery_task_id = models.CharField(max_length=64, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["tenant", "job_type", "created_at"]),
        ]
        ordering = ["-created_at"]
