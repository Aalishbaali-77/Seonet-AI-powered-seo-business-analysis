from __future__ import annotations

from django.db import models

from apps.common.models import TenantOwnedModel


class Campaign(TenantOwnedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        READY = "ready", "Ready"
        SENT = "sent", "Sent"
        CANCELLED = "cancelled", "Cancelled"

    class Channel(models.TextChoices):
        EMAIL = "email", "Email"
        OFFER = "offer", "Offer"
        CONTENT = "content", "Content"

    class Audience(models.TextChoices):
        LEAD_LIST = "lead_list", "Lead list"
        COMMERCE_CITY = "commerce_city", "Imported customers in a city"
        OPPORTUNITY = "opportunity", "Opportunity-linked leads"

    name = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    channel = models.CharField(max_length=20, choices=Channel.choices, default=Channel.OFFER)
    audience_type = models.CharField(max_length=32, choices=Audience.choices, default=Audience.LEAD_LIST)
    lead_list = models.ForeignKey("leads.LeadList", on_delete=models.SET_NULL, null=True, blank=True, related_name="campaigns")
    city = models.CharField(max_length=160, blank=True)
    opportunity = models.ForeignKey("opportunities.Opportunity", on_delete=models.SET_NULL, null=True, blank=True, related_name="campaigns")
    offer_title = models.CharField(max_length=255, blank=True)
    offer_body = models.TextField(blank=True)
    audience_count = models.PositiveIntegerField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    send_note = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["tenant", "status"])]
