from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.common.models import TenantOwnedModel


class Pipeline(TenantOwnedModel):
    name = models.CharField(max_length=120)
    is_default = models.BooleanField(default=False)


class Stage(TenantOwnedModel):
    pipeline = models.ForeignKey(Pipeline, on_delete=models.CASCADE, related_name="stages")
    name = models.CharField(max_length=80)
    code = models.CharField(max_length=40)
    order = models.PositiveSmallIntegerField(default=0)
    is_won = models.BooleanField(default=False)
    is_lost = models.BooleanField(default=False)

    class Meta:
        ordering = ["order"]
        unique_together = ("pipeline", "code")


class Company(TenantOwnedModel):
    name = models.CharField(max_length=255)
    domain = models.CharField(max_length=255, blank=True)
    industry = models.CharField(max_length=160, blank=True)
    location = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    notes = models.TextField(blank=True)
    tags = models.JSONField(default=list, blank=True)
    last_activity_at = models.DateTimeField(null=True, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_crm_companies",
    )


class Contact(TenantOwnedModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="contacts")
    first_name = models.CharField(max_length=120)
    last_name = models.CharField(max_length=120, blank=True)
    title = models.CharField(max_length=160, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_crm_contacts",
    )


class Deal(TenantOwnedModel):
    pipeline = models.ForeignKey(Pipeline, on_delete=models.CASCADE, related_name="deals")
    stage = models.ForeignKey(Stage, on_delete=models.PROTECT, related_name="deals")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="deals")
    contact = models.ForeignKey("Contact", on_delete=models.SET_NULL, null=True, blank=True, related_name="deals")
    name = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=8, default="PKR")
    expected_close_at = models.DateField(null=True, blank=True)
    lead = models.ForeignKey("leads.Lead", on_delete=models.SET_NULL, null=True, blank=True, related_name="deals")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_crm_deals",
    )
    priority = models.CharField(max_length=16, default="normal")
    next_step = models.CharField(max_length=255, blank=True)
    won_reason = models.CharField(max_length=255, blank=True)
    lost_reason = models.CharField(max_length=255, blank=True)
    closed_at = models.DateField(null=True, blank=True)
    last_activity_at = models.DateTimeField(null=True, blank=True)


class Activity(TenantOwnedModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="activities", null=True, blank=True)
    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name="activities", null=True, blank=True)
    contact = models.ForeignKey(Contact, on_delete=models.SET_NULL, null=True, blank=True, related_name="activities")
    kind = models.CharField(max_length=40, default="note")
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_crm_activities",
    )
