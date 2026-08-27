from __future__ import annotations

from decimal import Decimal

from django.db import models
from django.utils import timezone

from apps.common.encryption import EncryptedJSONField
from apps.common.models import TenantOwnedModel, TimeStampedModel, UUIDPrimaryKeyModel


class ProductModule(UUIDPrimaryKeyModel, TimeStampedModel):
    code = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=80)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=40, default="operations")
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self) -> str:
        return self.name


class ModuleFeature(UUIDPrimaryKeyModel, TimeStampedModel):
    module = models.ForeignKey(ProductModule, on_delete=models.CASCADE, related_name="features")
    code = models.CharField(max_length=80)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("module", "code")
        ordering = ["module__sort_order", "code"]

    def __str__(self) -> str:
        return self.code


class Plan(UUIDPrimaryKeyModel, TimeStampedModel):
    class Interval(models.TextChoices):
        MONTH = "month", "Monthly"
        YEAR = "year", "Yearly"

    code = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=80)
    description = models.TextField(blank=True)
    price_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=3, default="USD")
    interval = models.CharField(max_length=16, choices=Interval.choices, default=Interval.MONTH)
    trial_days = models.PositiveIntegerField(default=14)
    max_pages = models.PositiveIntegerField(default=25)
    max_audits_per_month = models.PositiveIntegerField(default=20)
    ai_credits = models.PositiveIntegerField(default=1000)
    max_users = models.PositiveIntegerField(default=5)
    is_active = models.BooleanField(default=True)
    is_public = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    cta_label = models.CharField(max_length=80, blank=True)
    cta_href = models.CharField(max_length=240, blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self) -> str:
        return self.name


class PlanModule(UUIDPrimaryKeyModel, TimeStampedModel):
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="plan_modules")
    module = models.ForeignKey(ProductModule, on_delete=models.CASCADE, related_name="plan_modules")
    is_included = models.BooleanField(default=True)
    limits = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ("plan", "module")


class PlanFeature(UUIDPrimaryKeyModel, TimeStampedModel):
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="plan_features")
    feature = models.ForeignKey(ModuleFeature, on_delete=models.CASCADE, related_name="plan_features")
    is_enabled = models.BooleanField(default=True)
    limit_value = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        unique_together = ("plan", "feature")


class TenantModule(TenantOwnedModel):
    class Source(models.TextChoices):
        PLAN = "plan", "Plan"
        OVERRIDE = "override", "Override"

    module = models.ForeignKey(ProductModule, on_delete=models.CASCADE, related_name="tenant_assignments")
    is_enabled = models.BooleanField(default=True)
    source = models.CharField(max_length=16, choices=Source.choices, default=Source.PLAN)
    limits = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ("tenant", "module")
        indexes = [
            models.Index(fields=["tenant", "is_enabled"]),
        ]


class PaymentGateway(UUIDPrimaryKeyModel, TimeStampedModel):
    class Provider(models.TextChoices):
        MANUAL = "manual", "Manual"
        STRIPE = "stripe", "Stripe"
        PAYPAL = "paypal", "PayPal"

    code = models.CharField(max_length=40, unique=True)
    provider = models.CharField(max_length=32, choices=Provider.choices)
    display_name = models.CharField(max_length=80)
    is_enabled = models.BooleanField(default=False)
    is_default = models.BooleanField(default=False)
    test_mode = models.BooleanField(default=True)
    public_config = models.JSONField(default=dict, blank=True)
    encrypted_config = EncryptedJSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-is_default", "display_name"]

    @property
    def credentials_configured(self) -> bool:
        return bool(self.encrypted_config)

    def __str__(self) -> str:
        return self.display_name


class Subscription(TenantOwnedModel):
    class Status(models.TextChoices):
        TRIALING = "trialing", "Trialing"
        ACTIVE = "active", "Active"
        PAST_DUE = "past_due", "Past due"
        EXPIRED = "expired", "Expired"
        CANCELED = "canceled", "Canceled"

    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="subscriptions")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TRIALING, db_index=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    seats = models.PositiveIntegerField(default=1)
    gateway = models.ForeignKey(PaymentGateway, on_delete=models.SET_NULL, null=True, blank=True, related_name="subscriptions")


class Invoice(TenantOwnedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ISSUED = "issued", "Issued"
        PAID = "paid", "Paid"
        VOID = "void", "Void"
        OVERDUE = "overdue", "Overdue"

    number = models.CharField(max_length=32, unique=True)
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True, blank=True, related_name="invoices")
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True, blank=True, related_name="invoices")
    gateway = models.ForeignKey(PaymentGateway, on_delete=models.SET_NULL, null=True, blank=True, related_name="invoices")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT, db_index=True)
    currency = models.CharField(max_length=3, default="USD")
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    due_at = models.DateTimeField(null=True, blank=True)
    issued_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    external_id = models.CharField(max_length=80, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "status", "created_at"]),
        ]
        ordering = ["-created_at"]

    def recast_status(self) -> None:
        if self.status in {self.Status.PAID, self.Status.VOID, self.Status.DRAFT}:
            return
        if self.due_at and self.due_at < timezone.now():
            self.status = self.Status.OVERDUE


class InvoiceLine(UUIDPrimaryKeyModel, TimeStampedModel):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="lines")
    description = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    unit_amount = models.DecimalField(max_digits=12, decimal_places=2)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
