from __future__ import annotations

from django.db import models
from django.core.validators import MaxValueValidator
from apps.common.models import TimeStampedModel, TenantOwnedModel, UUIDPrimaryKeyModel


class GeoPlace(UUIDPrimaryKeyModel, TimeStampedModel):
    class Kind(models.TextChoices):
        COUNTRY = "country", "Country"
        REGION = "region", "Region"
        CITY = "city", "City"
        AREA = "area", "Area"

    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="children")
    kind = models.CharField(max_length=20, choices=Kind.choices, db_index=True)
    code = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=160)
    country_code = models.CharField(max_length=8, default="PK")

    class Meta:
        indexes = [models.Index(fields=["kind", "country_code"]), models.Index(fields=["parent", "kind"])]
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class ScoringProfile(TenantOwnedModel):
    weights = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["tenant"], condition=models.Q(deleted_at__isnull=True), name="markets_one_scoring_profile")]


class MarketFocus(TenantOwnedModel):
    place = models.ForeignKey(GeoPlace, on_delete=models.CASCADE, related_name="tenant_focuses")
    notes = models.TextField(blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["tenant", "place"], condition=models.Q(deleted_at__isnull=True), name="markets_unique_focus")]


class MarketSignal(TenantOwnedModel):
    class Kind(models.TextChoices):
        DEMAND = "demand", "Demand"
        TARGET_CATEGORY = "target_category", "Target category"
        PURCHASING_POWER = "purchasing_power", "Purchasing power"
        POPULATION = "population", "Population"
        COMPETITION_GAP = "competition_gap", "Competition gap"
        BUSINESS_DENSITY = "business_density", "Business density"
        GROWTH_SIGNALS = "growth_signals", "Growth signals"
        SEARCH_INTEREST = "search_interest", "Search interest"

    class Verification(models.TextChoices):
        VERIFIED = "verified", "Verified"
        UNVERIFIED = "unverified", "Unverified"
        ESTIMATED = "estimated", "Estimated"
        INFERRED = "inferred", "Inferred"
        STALE = "stale", "Stale"

    place = models.ForeignKey(GeoPlace, on_delete=models.CASCADE, related_name="signals")
    kind = models.CharField(max_length=40, choices=Kind.choices, db_index=True)
    value = models.PositiveSmallIntegerField(validators=[MaxValueValidator(100)])
    source = models.CharField(max_length=120)
    source_url = models.URLField(blank=True)
    source_provider = models.CharField(max_length=80, blank=True)
    retrieved_at = models.DateTimeField(null=True, blank=True)
    confidence = models.FloatField(null=True, blank=True)
    verification_status = models.CharField(max_length=20, choices=Verification.choices, default=Verification.UNVERIFIED)

    class Meta:
        indexes = [models.Index(fields=["tenant", "place", "kind"])]
