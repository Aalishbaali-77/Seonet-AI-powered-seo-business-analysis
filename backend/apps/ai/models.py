from __future__ import annotations

from django.db import models

from apps.common.models import TenantOwnedModel, TimeStampedModel, UUIDPrimaryKeyModel


class PromptTemplate(UUIDPrimaryKeyModel, TimeStampedModel):
    key = models.CharField(max_length=80, unique=True)
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)


class PromptVersion(UUIDPrimaryKeyModel, TimeStampedModel):
    template = models.ForeignKey(PromptTemplate, on_delete=models.CASCADE, related_name="versions")
    version = models.PositiveIntegerField()
    body = models.TextField()
    is_active = models.BooleanField(default=False)

    class Meta:
        unique_together = ("template", "version")


class AIRequest(TenantOwnedModel):
    user = models.ForeignKey("users.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="ai_requests")
    provider = models.CharField(max_length=40)
    model = models.CharField(max_length=80, blank=True)
    task = models.CharField(max_length=80)
    status = models.CharField(max_length=20, default="completed")
    prompt = models.TextField(blank=True)
    untrusted_input = models.TextField(blank=True)
    response_text = models.TextField(blank=True)
    prompt_tokens = models.PositiveIntegerField(default=0)
    completion_tokens = models.PositiveIntegerField(default=0)
    cost = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    duration_ms = models.PositiveIntegerField(default=0)
    error = models.TextField(blank=True)
    request_id = models.CharField(max_length=64, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "created_at"]),
            models.Index(fields=["tenant", "provider"]),
            models.Index(fields=["task", "created_at"]),
        ]


class AskQuery(TenantOwnedModel):
    user = models.ForeignKey("users.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="ask_queries")
    question = models.TextField()
    intent = models.CharField(max_length=80, blank=True)
    origin = models.CharField(max_length=40, blank=True)
    facts = models.JSONField(default=list, blank=True)
    why = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "created_at"]),
        ]
        ordering = ["-created_at"]
