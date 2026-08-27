from __future__ import annotations

from django.db import models

from apps.common.models import TenantOwnedModel


class Website(TenantOwnedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        ARCHIVED = "archived", "Archived"

    url = models.URLField(max_length=500)
    domain = models.CharField(max_length=255, db_index=True)
    name = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    business_name = models.CharField(max_length=255, blank=True)
    industry = models.CharField(max_length=120, blank=True)
    description = models.TextField(blank=True)
    target_markets = models.JSONField(default=list, blank=True)
    keywords = models.JSONField(default=list, blank=True)
    competitors = models.JSONField(default=list, blank=True)
    audit_config = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "domain"]),
            models.Index(fields=["tenant", "status", "updated_at"]),
        ]
        unique_together = ("tenant", "domain")

    def __str__(self) -> str:
        return self.domain or self.url


class WebsiteAccess(TenantOwnedModel):
    class Kind(models.TextChoices):
        WORDPRESS = "wordpress", "WordPress"
        FTP = "ftp", "FTP"
        SFTP = "sftp", "SFTP / VPS"
        CPANEL = "cpanel", "cPanel FTP"

    class Status(models.TextChoices):
        DISCONNECTED = "disconnected", "Disconnected"
        CONNECTED = "connected", "Connected"
        ERROR = "error", "Error"

    website = models.OneToOneField(Website, on_delete=models.CASCADE, related_name="code_access")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DISCONNECTED, db_index=True)
    config = models.JSONField(default=dict, blank=True)
    secret_blob = models.TextField(blank=True)
    last_tested_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "website"]),
        ]

    def __str__(self) -> str:
        return f"{self.kind} @ {self.website_id}"


class AuditFixRun(TenantOwnedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPLYING = "applying", "Applying"
        REAUDITING = "reauditing", "Re-auditing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    website = models.ForeignKey(Website, on_delete=models.CASCADE, related_name="fix_runs")
    access = models.ForeignKey(WebsiteAccess, on_delete=models.SET_NULL, null=True, blank=True, related_name="fix_runs")
    baseline_audit = models.ForeignKey("audits.Audit", on_delete=models.PROTECT, related_name="fix_runs_as_baseline")
    followup_audit = models.ForeignKey("audits.Audit", on_delete=models.SET_NULL, null=True, blank=True, related_name="fix_runs_as_followup")
    job = models.ForeignKey("jobs.Job", on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_fix_runs")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    plan = models.JSONField(default=dict, blank=True)
    result = models.JSONField(default=dict, blank=True)
    comparison = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "website", "created_at"]),
        ]


class KeywordRankRun(TenantOwnedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    website = models.ForeignKey(Website, on_delete=models.CASCADE, related_name="keyword_runs")
    job = models.ForeignKey("jobs.Job", on_delete=models.SET_NULL, null=True, blank=True, related_name="keyword_rank_runs")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    source = models.CharField(max_length=40, blank=True)
    keywords = models.JSONField(default=list, blank=True)
    results = models.JSONField(default=list, blank=True)
    suggestions = models.JSONField(default=list, blank=True)
    ai = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "website", "created_at"]),
        ]
