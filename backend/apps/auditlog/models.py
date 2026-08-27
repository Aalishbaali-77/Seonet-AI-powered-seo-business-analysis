from __future__ import annotations

from django.db import models

from apps.common.models import TenantOwnedModel, TimeStampedModel, UUIDPrimaryKeyModel


class AuditLog(UUIDPrimaryKeyModel, TimeStampedModel):
    class Scope(models.TextChoices):
        WORKSPACE = "workspace", "Workspace"
        PLATFORM = "platform", "Platform"

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    user = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    scope = models.CharField(max_length=20, choices=Scope.choices, default=Scope.WORKSPACE, db_index=True)
    action = models.CharField(max_length=80, db_index=True)
    resource_type = models.CharField(max_length=80, blank=True)
    resource_id = models.CharField(max_length=64, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)
    request_id = models.CharField(max_length=64, blank=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "created_at"]),
            models.Index(fields=["tenant", "scope", "created_at"]),
            models.Index(fields=["scope", "created_at"]),
            models.Index(fields=["action", "created_at"]),
            models.Index(fields=["resource_type", "resource_id"]),
        ]
        ordering = ["-created_at"]


class PageView(TenantOwnedModel):
    user = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="page_views",
    )
    path = models.CharField(max_length=512, db_index=True)
    title = models.CharField(max_length=160, blank=True)
    referrer = models.CharField(max_length=512, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "created_at"]),
            models.Index(fields=["path", "created_at"]),
        ]
        ordering = ["-created_at"]
