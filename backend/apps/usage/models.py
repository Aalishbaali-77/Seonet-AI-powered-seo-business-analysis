from __future__ import annotations

from django.db import models

from apps.common.models import TenantOwnedModel


class UsageRecord(TenantOwnedModel):
    user = models.ForeignKey("users.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="usage_records")
    event_type = models.CharField(max_length=80, db_index=True)
    quantity = models.PositiveIntegerField(default=1)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "event_type", "created_at"]),
        ]
        ordering = ["-created_at"]
