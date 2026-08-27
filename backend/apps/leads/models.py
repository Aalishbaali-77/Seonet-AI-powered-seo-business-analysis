from __future__ import annotations

from django.db import models

from apps.common.models import TenantOwnedModel


class ICP(TenantOwnedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        CONFIRMED = "confirmed", "Confirmed"

    name = models.CharField(max_length=160)
    raw_input = models.TextField(blank=True)
    industry = models.CharField(max_length=160, blank=True)
    employee_count = models.CharField(max_length=40, blank=True)
    locations = models.JSONField(default=list, blank=True)
    keywords = models.JSONField(default=list, blank=True)
    origin = models.CharField(max_length=32, default="heuristic")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)


class LeadSearch(TenantOwnedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    icp = models.ForeignKey(ICP, on_delete=models.CASCADE, related_name="searches")
    job = models.ForeignKey("jobs.Job", on_delete=models.SET_NULL, null=True, blank=True, related_name="lead_searches")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    zones = models.PositiveIntegerField(default=0)
    queries = models.PositiveIntegerField(default=0)
    discovered = models.PositiveIntegerField(default=0)
    duplicates = models.PositiveIntegerField(default=0)
    unique_count = models.PositiveIntegerField(default=0)
    qualified = models.PositiveIntegerField(default=0)
    error = models.TextField(blank=True)


class LeadList(TenantOwnedModel):
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)


class Lead(TenantOwnedModel):
    class Status(models.TextChoices):
        NEW = "new", "New"
        QUALIFIED = "qualified", "Qualified"
        CONTACTED = "contacted", "Contacted"
        UNQUALIFIED = "unqualified", "Unqualified"

    search = models.ForeignKey(LeadSearch, on_delete=models.SET_NULL, null=True, blank=True, related_name="leads")
    lists = models.ManyToManyField(LeadList, blank=True, related_name="leads")
    company_name = models.CharField(max_length=255)
    industry = models.CharField(max_length=160, blank=True)
    location = models.CharField(max_length=255, blank=True)
    website = models.URLField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    linkedin_url = models.URLField(blank=True)
    description = models.TextField(blank=True)
    employee_count = models.CharField(max_length=40, blank=True)
    enriched_at = models.DateTimeField(null=True, blank=True)
    enrichment = models.JSONField(default=list, blank=True)
    source = models.CharField(max_length=80, default="manual")
    source_record_id = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW, db_index=True)
    lead_score = models.PositiveSmallIntegerField(null=True, blank=True, db_index=True)
    opportunity_score = models.PositiveSmallIntegerField(null=True, blank=True)
    quality_score = models.PositiveSmallIntegerField(null=True, blank=True)
    icp_fit = models.PositiveSmallIntegerField(null=True, blank=True)
    location_fit = models.PositiveSmallIntegerField(null=True, blank=True)
    industry_fit = models.PositiveSmallIntegerField(null=True, blank=True)
    crm_synced = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    ai_summary = models.TextField(blank=True)
    origin = models.CharField(max_length=32, default="fact")

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "status", "lead_score"]),
            models.Index(fields=["tenant", "company_name"]),
        ]
        unique_together = ("tenant", "source", "source_record_id")
