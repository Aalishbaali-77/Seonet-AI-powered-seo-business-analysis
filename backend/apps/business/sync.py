from __future__ import annotations

from decimal import Decimal

from django.utils.dateparse import parse_datetime

from apps.business.models import CatalogProduct, CommerceCustomer, CommerceOrder, CommerceOrderItem, CommerceReview
from apps.business.stores import COMMERCE_PROVIDERS, fetch_store
from apps.business.stores.http import money
from apps.common.exceptions import APIError
from apps.integrations.models import CRMConnection
from apps.jobs import services as job_services


def sentiment_from_rating(rating) -> str:
    try:
        value = int(rating)
    except (TypeError, ValueError):
        return ""
    if value >= 4:
        return CommerceReview.Sentiment.POSITIVE
    if value <= 2:
        return CommerceReview.Sentiment.NEGATIVE
    return CommerceReview.Sentiment.NEUTRAL


def _upsert_product(tenant, source: str, payload: dict) -> CatalogProduct | None:
    name = (payload.get("name") or "").strip()
    external_id = str(payload.get("external_id") or "").strip()
    if not name:
        return None
    lookup = CatalogProduct.objects.for_tenant(tenant).filter(source=source)
    product = lookup.filter(external_id=external_id).first() if external_id else None
    if product is None and payload.get("sku"):
        product = lookup.filter(sku=payload["sku"]).first()
    if product is None:
        product = CatalogProduct(tenant=tenant, source=source)
    product.name = name[:255]
    product.sku = str(payload.get("sku") or "")[:80]
    product.category = str(payload.get("category") or "")[:160]
    product.external_id = external_id[:80]
    product.unit_price = money(payload.get("unit_price"))
    product.verification_status = "imported"
    product.save()
    return product


def _safe_email(raw) -> str:
    from django.core.exceptions import ValidationError
    from django.core.validators import validate_email

    value = str(raw or "").strip()
    if not value:
        return ""
    try:
        validate_email(value)
    except ValidationError:
        return ""
    return value[:254]


def _upsert_customer(tenant, source: str, payload: dict) -> CommerceCustomer | None:
    name = (payload.get("name") or "").strip()
    if not name:
        return None
    external_id = str(payload.get("external_id") or "").strip()
    email = _safe_email(payload.get("email"))
    lookup = CommerceCustomer.objects.for_tenant(tenant).filter(source=source)
    customer = lookup.filter(external_id=external_id).first() if external_id else None
    if customer is None and email:
        customer = lookup.filter(email=email).first()
    if customer is None:
        customer = lookup.filter(name=name[:255]).first()
    if customer is None:
        customer = CommerceCustomer(tenant=tenant, source=source)
    customer.name = name[:255]
    customer.email = email
    customer.city = str(payload.get("city") or "")[:160]
    customer.external_id = external_id[:80]
    customer.verification_status = "imported"
    customer.save()
    return customer


def apply_payload(tenant, source: str, payload: dict) -> dict:
    products = 0
    product_map: dict[str, CatalogProduct] = {}
    for row in payload.get("products") or []:
        product = _upsert_product(tenant, source, row)
        if product is None:
            continue
        products += 1
        if product.external_id:
            product_map[product.external_id] = product
    orders = 0
    for row in payload.get("orders") or []:
        external_id = str(row.get("external_id") or "").strip()
        if not external_id:
            continue
        customer = _upsert_customer(tenant, source, row.get("customer") or {})
        order = CommerceOrder.objects.for_tenant(tenant).filter(source=source, external_id=external_id).first()
        if order is None:
            order = CommerceOrder(tenant=tenant, source=source, external_id=external_id[:80])
        order.customer = customer
        order.city = str(row.get("city") or (customer.city if customer else ""))[:160]
        order.channel = source
        order.currency = str(row.get("currency") or "USD")[:8]
        order.status = row.get("status") if row.get("status") in {choice[0] for choice in CommerceOrder.Status.choices} else CommerceOrder.Status.PLACED
        ordered_at = row.get("ordered_at")
        order.ordered_at = parse_datetime(str(ordered_at)) if ordered_at else None
        order.save()
        for item in order.items.all():
            item.hard_delete()
        for line in row.get("lines") or []:
            product = product_map.get(str(line.get("product_external_id") or ""))
            if product is None and line.get("sku"):
                product = CatalogProduct.objects.for_tenant(tenant).filter(source=source, sku=line["sku"]).first()
            CommerceOrderItem.objects.create(
                tenant=tenant,
                order=order,
                product=product,
                sku=str(line.get("sku") or "")[:80],
                name=str(line.get("name") or "")[:255],
                quantity=money(line.get("quantity")) or Decimal("1"),
                unit_price=money(line.get("unit_price")) or Decimal("0"),
                discount=money(line.get("discount")) or Decimal("0"),
            )
        orders += 1
    reviews = 0
    for row in payload.get("reviews") or []:
        external_id = str(row.get("external_id") or "").strip()
        if not external_id:
            continue
        review = CommerceReview.objects.for_tenant(tenant).filter(source=source, external_id=external_id).first()
        if review is None:
            review = CommerceReview(tenant=tenant, source=source, external_id=external_id[:80])
        product = product_map.get(str(row.get("product_external_id") or ""))
        review.product = product
        try:
            review.rating = int(float(row["rating"]))
        except (TypeError, ValueError):
            review.rating = None
        review.title = str(row.get("title") or "")[:255]
        review.body = str(row.get("body") or "")[:4000]
        review.reviewer = str(row.get("reviewer") or "")[:160]
        review.sentiment = sentiment_from_rating(review.rating)
        review.origin = "fact"
        review.save()
        reviews += 1
    return {"products": products, "orders": orders, "reviews": reviews}


def start_store_sync(*, tenant, user, provider: str):
    if provider not in COMMERCE_PROVIDERS:
        raise APIError("Unknown store.", code="NOT_FOUND", status_code=404)
    connection = CRMConnection.objects.filter(tenant=tenant, provider=provider).first()
    if connection is None or not connection.credentials_configured:
        raise APIError("Save store credentials before syncing.", code="VALIDATION_ERROR")
    job = job_services.create_job(tenant=tenant, user=user, job_type="sync_commerce", payload={"provider": provider})
    job.celery_task_id = _enqueue(str(job.id))
    job.save(update_fields=["celery_task_id", "updated_at"])
    job.refresh_from_db()
    return job


def _enqueue(job_id: str) -> str:
    from threading import Thread

    from django.conf import settings
    from django.db import connections, transaction

    from workers.tasks import sync_commerce

    eager = getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False)
    propagate = getattr(settings, "CELERY_TASK_EAGER_PROPAGATES", False)
    if eager and not propagate:
        def runner() -> None:
            connections.close_all()
            sync_commerce(job_id)

        transaction.on_commit(lambda: Thread(target=runner, daemon=True).start())
        return "thread"
    async_result = sync_commerce.delay(job_id)
    return str(async_result.id)


def execute_store_sync(job) -> dict:
    from django.utils import timezone

    from apps.auditlog.services import write_audit
    from apps.usage.services import record_usage

    provider = (job.payload or {}).get("provider")
    job_services.mark_running(job, progress=10, result={"stage": "Fetching store"})
    connection = CRMConnection.objects.filter(tenant=job.tenant, provider=provider).first()
    if connection is None:
        job_services.mark_failed(job, error="Store is not connected.")
        raise APIError("Store is not connected.", code="VALIDATION_ERROR")
    try:
        payload = fetch_store(provider, public=connection.config or {}, secret=connection.encrypted_config or {})
        counts = apply_payload(job.tenant, provider, payload)
    except Exception as exc:  # noqa: BLE001
        connection.status = CRMConnection.Status.ERROR
        connection.last_error = str(exc)[:500]
        connection.last_checked_at = timezone.now()
        connection.save(update_fields=["status", "last_error", "last_checked_at", "updated_at"])
        job_services.mark_failed(job, error=str(exc)[:4000])
        return {"error": str(exc)[:500]}
    connection.status = CRMConnection.Status.CONNECTED
    connection.last_error = ""
    connection.last_sync_at = timezone.now()
    connection.last_checked_at = timezone.now()
    connection.records_synced = int(counts["products"]) + int(counts["orders"]) + int(counts["reviews"])
    connection.save(update_fields=["status", "last_error", "last_sync_at", "last_checked_at", "records_synced", "updated_at"])
    record_usage(tenant=job.tenant, user=job.user, event_type="commerce_imported", quantity=connection.records_synced, metadata={"kind": "store", "provider": provider, **counts})
    write_audit(action="COMMERCE_SYNCED", tenant=job.tenant, user=job.user, resource_type="integration", resource_id=connection.id, metadata={"provider": provider, **counts})
    from apps.billing.entitlements import tenant_module_codes
    from apps.business.analysis import complete_analysis

    summary = complete_analysis(tenant=job.tenant, user=job.user, run_ai="ai" in tenant_module_codes(job.tenant))
    job_services.mark_completed(
        job,
        result={
            "stage": "Analyzed",
            **counts,
            "opportunities_created": summary.get("opportunities_created") or 0,
            "analysis_available": bool((summary.get("analysis") or {}).get("available")),
            "expert_origin": (summary.get("expert") or {}).get("origin") or "",
        },
    )
    return counts


def promote_customers_to_leads(tenant) -> dict:
    from apps.billing.entitlements import tenant_module_codes
    from apps.leads.models import Lead
    from apps.leads.scoring import apply_lead_score

    if "leads" not in tenant_module_codes(tenant):
        raise APIError("Lead Intelligence is not on this package.", code="FEATURE_DISABLED", status_code=403)
    created = 0
    skipped = 0
    for customer in CommerceCustomer.objects.for_tenant(tenant).exclude(name=""):
        record_id = f"{customer.source}:{customer.external_id or customer.id}"
        existing = Lead.objects.for_tenant(tenant).filter(source=customer.source or "commerce", source_record_id=record_id).first()
        if existing:
            skipped += 1
            continue
        lead = Lead.objects.create(
            tenant=tenant,
            company_name=customer.name[:255],
            email=customer.email,
            location=customer.city,
            source=customer.source or "commerce",
            source_record_id=record_id[:120],
            notes="Created from a stored commerce customer. This is an existing buyer, not a discovered prospect.",
            origin="fact",
        )
        apply_lead_score(lead)
        created += 1
    return {"created": created, "skipped": skipped}
