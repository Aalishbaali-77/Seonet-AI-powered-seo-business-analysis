from __future__ import annotations

from django.db import models

from apps.common.models import TenantOwnedModel


class Notification(TenantOwnedModel):
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    kind = models.CharField(max_length=40, default="info")
    link = models.CharField(max_length=400, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "user", "created_at"]),
        ]
        ordering = ["-created_at"]
