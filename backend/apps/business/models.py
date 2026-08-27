from __future__ import annotations

from django.db import models

from apps.common.models import TenantOwnedModel


class BusinessProfile(TenantOwnedModel):
    class BusinessType(models.TextChoices):
        ECOMMERCE = "ecommerce", "E-commerce"
        RETAIL = "retail", "Retail"
        SERVICES = "services", "Services"
        B2B = "b2b", "B2B"
        MANUFACTURING = "manufacturing", "Manufacturing"

    business_type = models.CharField(max_length=32, choices=BusinessType.choices, default=BusinessType.ECOMMERCE)
    industry = models.CharField(max_length=160, blank=True)
    category = models.CharField(max_length=160, blank=True)
    current_market = models.CharField(max_length=160, blank=True)
    goal = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    last_expert = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["tenant"], condition=models.Q(deleted_at__isnull=True), name="business_one_profile_per_tenant")]


class CatalogProduct(TenantOwnedModel):
    sku = models.CharField(max_length=80, blank=True)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=160, blank=True)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    cost_price = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    external_id = models.CharField(max_length=80, blank=True)
    source = models.CharField(max_length=80, default="csv")
    verification_status = models.CharField(max_length=20, default="unverified")

    class Meta:
        indexes = [models.Index(fields=["tenant", "sku"]), models.Index(fields=["tenant", "source", "external_id"])]


class CommerceCustomer(TenantOwnedModel):
    name = models.CharField(max_length=255)
    city = models.CharField(max_length=160, blank=True)
    email = models.EmailField(blank=True)
    external_id = models.CharField(max_length=80, blank=True)
    source = models.CharField(max_length=80, default="csv")
    verification_status = models.CharField(max_length=20, default="unverified")


class ImportBatch(TenantOwnedModel):
    class Kind(models.TextChoices):
        ORDERS = "orders", "Orders"
        PRODUCTS = "products", "Products"

    class Status(models.TextChoices):
        SUCCESS = "success", "Success"
        PARTIAL = "partial", "Partial"
        FAILED = "failed", "Failed"

    job = models.ForeignKey("jobs.Job", on_delete=models.SET_NULL, null=True, blank=True, related_name="import_batches")
    file_name = models.CharField(max_length=255, blank=True)
    kind = models.CharField(max_length=20, choices=Kind.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUCCESS)
    rows_total = models.PositiveIntegerField(default=0)
    rows_imported = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [models.Index(fields=["tenant", "kind", "created_at"])]


class CommerceOrder(TenantOwnedModel):
    class Status(models.TextChoices):
        PLACED = "placed", "Placed"
        CANCELLED = "cancelled", "Cancelled"
        RETURNED = "returned", "Returned"
        REFUNDED = "refunded", "Refunded"

    external_id = models.CharField(max_length=80, blank=True)
    ordered_at = models.DateTimeField(null=True, blank=True)
    customer = models.ForeignKey(CommerceCustomer, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders")
    city = models.CharField(max_length=160, blank=True)
    channel = models.CharField(max_length=80, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLACED, db_index=True)
    currency = models.CharField(max_length=8, default="PKR")
    source = models.CharField(max_length=80, default="csv")
    import_batch = models.ForeignKey(ImportBatch, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders")

    class Meta:
        indexes = [models.Index(fields=["tenant", "ordered_at"])]


class CommerceOrderItem(TenantOwnedModel):
    order = models.ForeignKey(CommerceOrder, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(CatalogProduct, on_delete=models.SET_NULL, null=True, blank=True, related_name="order_items")
    sku = models.CharField(max_length=80, blank=True)
    name = models.CharField(max_length=255, blank=True)
    quantity = models.DecimalField(max_digits=12, decimal_places=3, default=1)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    cost = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)


class CommerceReview(TenantOwnedModel):
    class Sentiment(models.TextChoices):
        POSITIVE = "positive", "Positive"
        NEUTRAL = "neutral", "Neutral"
        NEGATIVE = "negative", "Negative"

    product = models.ForeignKey(CatalogProduct, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviews")
    external_id = models.CharField(max_length=80, blank=True)
    rating = models.PositiveSmallIntegerField(null=True, blank=True)
    title = models.CharField(max_length=255, blank=True)
    body = models.TextField(blank=True)
    reviewer = models.CharField(max_length=160, blank=True)
    source = models.CharField(max_length=80)
    sentiment = models.CharField(max_length=16, choices=Sentiment.choices, blank=True)
    origin = models.CharField(max_length=32, default="fact")

    class Meta:
        indexes = [models.Index(fields=["tenant", "source", "created_at"])]
