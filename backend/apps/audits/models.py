from __future__ import annotations

from django.db import models

from apps.common.models import TenantOwnedModel


class Crawl(TenantOwnedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    website = models.ForeignKey("websites.Website", on_delete=models.CASCADE, related_name="crawls")
    job = models.ForeignKey("jobs.Job", on_delete=models.SET_NULL, null=True, blank=True, related_name="crawls")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    pages_discovered = models.PositiveIntegerField(default=0)
    error = models.TextField(blank=True)
    signals = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)


class CrawlPage(TenantOwnedModel):
    crawl = models.ForeignKey(Crawl, on_delete=models.CASCADE, related_name="pages")
    url = models.URLField(max_length=800)
    status_code = models.PositiveSmallIntegerField(null=True, blank=True)
    title = models.CharField(max_length=500, blank=True)
    content_type = models.CharField(max_length=80, blank=True)
    extracted = models.JSONField(default=dict, blank=True)
    origin = models.CharField(max_length=20, default="fact")
    ttfb_ms = models.PositiveIntegerField(null=True, blank=True)
    html_size_bytes = models.PositiveIntegerField(default=0)
    transfer_bytes = models.PositiveIntegerField(default=0)
    compression = models.CharField(max_length=20, blank=True)
    http_protocol = models.CharField(max_length=20, blank=True)
    page_score = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "created_at"]),
            models.Index(fields=["tenant", "crawl", "ttfb_ms"]),
            models.Index(fields=["tenant", "crawl", "page_score"]),
        ]


class Audit(TenantOwnedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    website = models.ForeignKey("websites.Website", on_delete=models.CASCADE, related_name="audits")
    crawl = models.ForeignKey(Crawl, on_delete=models.SET_NULL, null=True, blank=True, related_name="audits")
    job = models.ForeignKey("jobs.Job", on_delete=models.SET_NULL, null=True, blank=True, related_name="audits")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    overall_score = models.PositiveSmallIntegerField(null=True, blank=True)
    scores = models.JSONField(default=dict, blank=True)
    pages_crawled = models.PositiveIntegerField(default=0)
    issue_count = models.PositiveIntegerField(default=0)
    summary = models.JSONField(default=dict, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "website", "created_at"]),
            models.Index(fields=["tenant", "status"]),
        ]


class AuditIssue(TenantOwnedModel):
    class Severity(models.TextChoices):
        CRITICAL = "critical", "Critical"
        HIGH = "high", "High"
        MEDIUM = "medium", "Medium"
        LOW = "low", "Low"
        INFO = "info", "Info"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        RESOLVED = "resolved", "Resolved"
        IGNORED = "ignored", "Ignored"

    audit = models.ForeignKey(Audit, on_delete=models.CASCADE, related_name="issues")
    code = models.CharField(max_length=60, blank=True, db_index=True)
    severity = models.CharField(max_length=20, choices=Severity.choices, db_index=True)
    category = models.CharField(max_length=40, db_index=True)
    title = models.CharField(max_length=255)
    why_it_matters = models.TextField()
    affected_urls = models.JSONField(default=list, blank=True)
    evidence = models.TextField()
    recommendation = models.TextField()
    estimated_effort = models.CharField(max_length=40, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN, db_index=True)
    origin = models.CharField(max_length=32, default="fact")
    confidence = models.FloatField(null=True, blank=True)
    priority = models.PositiveSmallIntegerField(default=50)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "created_at"]),
            models.Index(fields=["tenant", "audit", "severity"]),
            models.Index(fields=["tenant", "audit", "code"]),
            models.Index(fields=["tenant", "audit", "category"]),
        ]


class AuditRecommendation(TenantOwnedModel):
    audit = models.ForeignKey(Audit, on_delete=models.CASCADE, related_name="recommendations")
    issue = models.ForeignKey(AuditIssue, on_delete=models.SET_NULL, null=True, blank=True, related_name="recommendation_rows")
    title = models.CharField(max_length=255)
    verified_finding = models.TextField()
    ai_interpretation = models.TextField(blank=True)
    recommendation = models.TextField()
    origin = models.CharField(max_length=32, default="recommendation")
    confidence = models.FloatField(null=True, blank=True)
