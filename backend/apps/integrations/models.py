from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.common.encryption import EncryptedJSONField
from apps.common.models import TenantOwnedModel


class CRMConnection(TenantOwnedModel):
    class Status(models.TextChoices):
        DISCONNECTED = "disconnected", "Disconnected"
        CONFIGURED = "configured", "Configured"
        CONNECTED = "connected", "Connected"
        ERROR = "error", "Error"

    provider = models.CharField(max_length=40, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DISCONNECTED, db_index=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)
    records_synced = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True)
    config = models.JSONField(default=dict, blank=True)
    encrypted_config = EncryptedJSONField(default=dict, blank=True)
    enabled = models.BooleanField(default=True)

    class Meta:
        unique_together = ("tenant", "provider")
        indexes = [
            models.Index(fields=["tenant", "created_at"]),
            models.Index(fields=["tenant", "provider"]),
        ]

    @property
    def credentials_configured(self) -> bool:
        return bool(self.encrypted_config)

    def __str__(self) -> str:
        return f"{self.provider} @ {self.tenant_id}"


class CRMFieldMapping(TenantOwnedModel):
    connection = models.ForeignKey(CRMConnection, on_delete=models.CASCADE, related_name="mappings")
    local_field = models.CharField(max_length=80)
    remote_field = models.CharField(max_length=80)


class TenantApiToken(TenantOwnedModel):
    name = models.CharField(max_length=80)
    prefix = models.CharField(max_length=24, db_index=True)
    hashed_key = models.CharField(max_length=64)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_api_tokens",
    )
    last_used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "created_at"]),
            models.Index(fields=["prefix"]),
        ]
        ordering = ["-created_at"]
