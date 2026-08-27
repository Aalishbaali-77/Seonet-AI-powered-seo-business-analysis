from __future__ import annotations

from django.db import models

from apps.common.models import TenantOwnedModel


class Opportunity(TenantOwnedModel):
    class Type(models.TextChoices):
        BUSINESS = "business", "Business"
        MARKET = "market", "Market"
        PRODUCT = "product", "Product"
        GEOGRAPHIC = "geographic", "Geographic"
        CUSTOMER = "customer", "Customer"
        CROSS_SELL = "cross_sell", "Cross-sell"
        UPSELL = "upsell", "Upsell"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        REVIEWING = "reviewing", "Reviewing"
        ACCEPTED = "accepted", "Accepted"
        DISMISSED = "dismissed", "Dismissed"

    title = models.CharField(max_length=255)
    type = models.CharField(max_length=32, choices=Type.choices, db_index=True)
    score = models.PositiveSmallIntegerField(null=True, blank=True)
    evidence = models.TextField()
    recommended_action = models.TextField()
    potential_impact = models.TextField(blank=True)
    confidence = models.PositiveSmallIntegerField(null=True, blank=True)
    origin = models.CharField(max_length=32, default="user")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN, db_index=True)
    geo_place = models.ForeignKey("markets.GeoPlace", on_delete=models.SET_NULL, null=True, blank=True, related_name="opportunities")
    related_leads = models.ManyToManyField("leads.Lead", blank=True, related_name="growth_opportunities")

    class Meta:
        indexes = [models.Index(fields=["tenant", "status", "type"])]
        ordering = ["-created_at"]
