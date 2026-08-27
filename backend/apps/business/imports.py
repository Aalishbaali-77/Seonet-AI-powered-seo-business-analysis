from __future__ import annotations

import csv
import io
import re
from collections.abc import Callable
from decimal import Decimal, InvalidOperation

from django.utils.dateparse import parse_datetime

from apps.business.models import CatalogProduct, CommerceCustomer, CommerceOrder, CommerceOrderItem, ImportBatch
from apps.common.exceptions import APIError

CSV_TEMPLATES = {
    "products": {
        "filename": "seonet-products-template.csv",
        "columns": ["name", "sku", "category", "unit_price", "cost_price"],
    },
    "orders": {
        "filename": "seonet-orders-template.csv",
        "columns": [
            "order_id",
            "ordered_at",
            "customer_name",
            "email",
            "city",
            "channel",
            "currency",
            "sku",
            "product_name",
            "quantity",
            "unit_price",
            "discount",
            "cost",
        ],
    },
}

HEADER_ALIASES = {
    "product": "name",
    "title": "name",
    "item": "name",
    "product_name": "name",
    "productname": "name",
    "code": "sku",
    "item_sku": "sku",
    "price": "unit_price",
    "unitprice": "unit_price",
    "sale_price": "unit_price",
    "cost": "cost_price",
    "costprice": "cost_price",
    "customer": "customer_name",
    "buyer": "customer_name",
    "qty": "quantity",
    "date": "ordered_at",
    "order_date": "ordered_at",
    "external_id": "order_id",
    "orderid": "order_id",
}

MAX_CSV_BYTES = 2_000_000
ProgressFn = Callable[[int, int], None]


def csv_template(kind: str) -> tuple[str, str]:
    spec = CSV_TEMPLATES.get(kind)
    if spec is None:
        raise ValueError("Unknown CSV template.")
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(spec["columns"])
    return spec["filename"], "\ufeff" + buf.getvalue()


def decode_csv_bytes(raw: bytes) -> str:
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16")
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig")
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _normalize_header(value: str) -> str:
    cleaned = (value or "").replace("\ufeff", "").strip().strip('"').strip("'").lower()
    cleaned = re.sub(r"[\s\-/]+", "_", cleaned)
    return HEADER_ALIASES.get(cleaned, cleaned)


def _strip_sep_line(text: str) -> tuple[str, str]:
    stripped = text.lstrip("\ufeff").lstrip()
    first, _, rest = stripped.partition("\n")
    marker = first.strip().replace(" ", "").lower()
    if marker.startswith("sep="):
        delimiter = first.split("=", 1)[-1].strip().strip('"')[:1] or ","
        return rest, delimiter
    return text, ""


def _sniff_delimiter(sample: str, forced: str = "") -> str:
    if forced:
        return forced
    header = next((line for line in sample.splitlines() if line.strip()), "")
    counts = {";": header.count(";"), "\t": header.count("\t"), "|": header.count("|"), ",": header.count(",")}
    best = max(counts, key=lambda key: counts[key])
    return best if counts[best] else ","


def parse_csv_rows(text: str, kind: str) -> tuple[list[dict[str, str]], dict]:
    spec = CSV_TEMPLATES.get(kind)
    if spec is None:
        raise ValueError("Unknown CSV template.")
    expected: list[str] = spec["columns"]
    body, forced = _strip_sep_line(text)
    delimiter = _sniff_delimiter(body, forced)
    reader = csv.reader(io.StringIO(body), delimiter=delimiter)
    try:
        raw_headers = next(reader)
    except StopIteration:
        return [], {"delimiter": delimiter, "positional": False, "headers": [], "warning": "The file has no header row."}
    headers = [_normalize_header(item) for item in raw_headers]
    if len(headers) == 1 and any(sep in raw_headers[0] for sep in (";", ",", "\t", "|")):
        delimiter = _sniff_delimiter(raw_headers[0])
        reader = csv.reader(io.StringIO(body), delimiter=delimiter)
        raw_headers = next(reader)
        headers = [_normalize_header(item) for item in raw_headers]
    named = {key for key in headers if key}
    required = {"name"} if kind == "products" else {"product_name", "name", "sku"}
    positional = not named.intersection(required) and not named.intersection(set(expected))
    if positional and kind == "orders" and "customer_name" in named:
        positional = False
    rows: list[dict[str, str]] = []
    for raw in reader:
        if not any(str(cell).strip() for cell in raw):
            continue
        if positional:
            mapped = {expected[index]: str(raw[index]).strip() if index < len(raw) else "" for index in range(len(expected))}
        else:
            mapped = {}
            for index, header in enumerate(headers):
                if not header:
                    continue
                key = "product_name" if kind == "orders" and header == "name" else header
                mapped[key] = str(raw[index]).strip() if index < len(raw) else ""
        rows.append(mapped)
    warning = ""
    if positional:
        warning = "Headers did not match the template, so columns were read in template order."
    elif kind == "products" and "name" not in named and "product_name" not in named:
        warning = f"Expected a name column. Found: {', '.join(h for h in headers if h) or 'none'}."
    return rows, {"delimiter": delimiter, "positional": positional, "headers": headers, "warning": warning}


def _cell(row: dict, *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _money(raw: str, *, delimiter: str = ",") -> Decimal | None:
    if not raw:
        return None
    value = re.sub(r"(rs\.?|pkr|usd|\$)", "", raw, flags=re.I).strip()
    if delimiter == ";" and "," in value and "." not in value:
        value = value.replace(".", "").replace(",", ".")
    else:
        value = value.replace(",", "")
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError):
        return None


def import_products_csv(tenant, text: str, *, on_progress: ProgressFn | None = None) -> dict:
    rows, meta = parse_csv_rows(text, "products")
    created = 0
    skipped = 0
    reasons: list[str] = []
    total = len(rows)
    delimiter = str(meta.get("delimiter") or ",")
    for index, row in enumerate(rows, start=1):
        name = _cell(row, "name", "product_name", "product", "title")
        if not name:
            skipped += 1
            if len(reasons) < 8:
                reasons.append(f"Row {index}: name is required.")
            continue
        CatalogProduct.objects.create(
            tenant=tenant,
            name=name[:255],
            sku=_cell(row, "sku", "code")[:80],
            category=_cell(row, "category")[:160],
            unit_price=_money(_cell(row, "unit_price", "price"), delimiter=delimiter),
            cost_price=_money(_cell(row, "cost_price", "cost"), delimiter=delimiter),
            source="csv",
            verification_status="unverified",
        )
        created += 1
        if on_progress:
            on_progress(index, total)
    return {
        "created": created,
        "skipped": skipped,
        "empty_rows": 0,
        "kind": "products",
        "skip_reasons": reasons,
        "warning": meta.get("warning") or "",
        "delimiter": delimiter,
    }


def import_orders_csv(tenant, text: str, *, batch: ImportBatch | None = None, on_progress: ProgressFn | None = None) -> dict:
    rows, meta = parse_csv_rows(text, "orders")
    created = 0
    skipped = 0
    duplicates = 0
    reasons: list[str] = []
    total = len(rows)
    delimiter = str(meta.get("delimiter") or ",")
    for index, row in enumerate(rows, start=1):
        name = _cell(row, "product_name", "name", "title")
        sku = _cell(row, "sku")[:80]
        if not name and not sku:
            skipped += 1
            if len(reasons) < 8:
                reasons.append(f"Row {index}: product_name or sku is required.")
            continue
        external_id = _cell(row, "order_id", "external_id")[:80]
        if external_id and CommerceOrder.objects.for_tenant(tenant).filter(external_id=external_id).exists():
            skipped += 1
            duplicates += 1
            if len(reasons) < 8:
                reasons.append(f"Row {index}: order {external_id} already imported, skipped as duplicate.")
            continue
        customer_name = _cell(row, "customer_name", "customer")
        customer = None
        if customer_name:
            customer, _ = CommerceCustomer.objects.get_or_create(
                tenant=tenant,
                name=customer_name[:255],
                defaults={"city": _cell(row, "city")[:160], "email": _cell(row, "email"), "source": "csv"},
            )
        product = CatalogProduct.objects.for_tenant(tenant).filter(sku=sku).first() if sku else None
        if product is None and name:
            product = CatalogProduct.objects.create(tenant=tenant, name=name[:255], sku=sku, source="csv")
        ordered_at = parse_datetime(_cell(row, "ordered_at", "date")) if _cell(row, "ordered_at", "date") else None
        order = CommerceOrder.objects.create(
            tenant=tenant,
            external_id=external_id,
            ordered_at=ordered_at,
            customer=customer,
            city=_cell(row, "city")[:160],
            channel=_cell(row, "channel")[:80] or "csv",
            currency=_cell(row, "currency")[:8] or "PKR",
            source="csv",
            import_batch=batch,
        )
        qty = _money(_cell(row, "quantity", "qty"), delimiter=delimiter) or Decimal("1")
        CommerceOrderItem.objects.create(
            tenant=tenant,
            order=order,
            product=product,
            sku=sku,
            name=(name or (product.name if product else ""))[:255],
            quantity=qty,
            unit_price=_money(_cell(row, "unit_price", "price"), delimiter=delimiter) or Decimal("0"),
            discount=_money(_cell(row, "discount"), delimiter=delimiter) or Decimal("0"),
            cost=_money(_cell(row, "cost"), delimiter=delimiter),
        )
        created += 1
        if on_progress:
            on_progress(index, total)
    return {
        "created": created,
        "skipped": skipped,
        "duplicates": duplicates,
        "empty_rows": 0,
        "kind": "orders",
        "skip_reasons": reasons,
        "warning": meta.get("warning") or "",
        "delimiter": delimiter,
    }


def start_csv_import(*, tenant, user, kind: str, raw: bytes, file_name: str = ""):
    from apps.jobs import services as job_services

    if kind not in CSV_TEMPLATES:
        raise APIError("Import products or orders.", code="VALIDATION_ERROR")
    if not raw:
        raise APIError("The CSV file is empty.", code="VALIDATION_ERROR")
    if len(raw) > MAX_CSV_BYTES:
        raise APIError("CSV is larger than 2 MB. Split the file and import again.", code="VALIDATION_ERROR")
    job = job_services.create_job(
        tenant=tenant,
        user=user,
        job_type="import_commerce",
        payload={"kind": kind, "csv_text": decode_csv_bytes(raw), "file_name": file_name[:255]},
    )
    job.celery_task_id = _enqueue(str(job.id))
    job.save(update_fields=["celery_task_id", "updated_at"])
    job.refresh_from_db()
    return job


def _enqueue(job_id: str) -> str:
    from threading import Thread

    from django.conf import settings
    from django.db import connections, transaction

    from workers.tasks import import_commerce

    eager = getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False)
    propagate = getattr(settings, "CELERY_TASK_EAGER_PROPAGATES", False)
    if eager and not propagate:
        def runner() -> None:
            connections.close_all()
            import_commerce(job_id)

        transaction.on_commit(lambda: Thread(target=runner, daemon=True).start())
        return "thread"
    async_result = import_commerce.delay(job_id)
    return str(async_result.id)


def execute_csv_import(job) -> dict:
    from apps.auditlog.services import write_audit
    from apps.jobs import services as job_services
    from apps.usage.services import record_usage

    kind = (job.payload or {}).get("kind") or "products"
    text = (job.payload or {}).get("csv_text") or ""
    file_name = (job.payload or {}).get("file_name") or ""
    job.payload = {"kind": kind}
    job.save(update_fields=["payload", "updated_at"])
    job_services.mark_running(job, progress=8, result={"stage": "Reading file", "kind": kind})

    def on_progress(done: int, total: int) -> None:
        if done == total or done % 10 == 0:
            pct = 15 + int((done / max(total, 1)) * 70)
            job_services.mark_progress(
                job,
                progress=pct,
                result={"stage": "Importing rows", "processed": done, "total": total, "kind": kind},
            )

    batch = None
    if kind == "orders":
        batch = ImportBatch.objects.create(tenant=job.tenant, job=job, file_name=file_name, kind=ImportBatch.Kind.ORDERS)
        result = import_orders_csv(job.tenant, text, batch=batch, on_progress=on_progress)
    else:
        result = import_products_csv(job.tenant, text, on_progress=on_progress)
    if batch is not None:
        created_count = int(result.get("created") or 0)
        skipped_count = int(result.get("skipped") or 0)
        batch.rows_total = created_count + skipped_count
        batch.rows_imported = created_count
        if created_count == 0:
            batch.status = ImportBatch.Status.FAILED
        elif skipped_count > 0:
            batch.status = ImportBatch.Status.PARTIAL
        else:
            batch.status = ImportBatch.Status.SUCCESS
        batch.save(update_fields=["rows_total", "rows_imported", "status", "updated_at"])
        result["import_batch_id"] = str(batch.id)
    record_usage(
        tenant=job.tenant,
        user=job.user,
        event_type="commerce_imported",
        quantity=int(result.get("created") or 0),
        metadata={"kind": kind, "skipped": int(result.get("skipped") or 0)},
    )
    write_audit(
        action="COMMERCE_IMPORTED",
        tenant=job.tenant,
        user=job.user,
        resource_type="business",
        metadata={"kind": kind, "created": result.get("created"), "skipped": result.get("skipped")},
    )
    if kind == "orders" and int(result.get("created") or 0) > 0:
        from apps.business.analysis import complete_analysis

        job_services.mark_progress(job, progress=88, result={"stage": "Analyzing", "kind": kind})
        summary = complete_analysis(tenant=job.tenant, user=job.user, run_ai=False)
        result["opportunities_created"] = summary.get("opportunities_created") or 0
    if int(result.get("created") or 0) == 0:
        reasons = result.get("skip_reasons") or []
        warning = result.get("warning") or ""
        if int(result.get("skipped") or 0) == 0:
            message = "No data rows found. Download the template, fill your rows under the header, then import."
        else:
            message = warning or "No rows could be imported. Keep the header row from the template (name, sku, category, unit_price, cost_price)."
            if reasons:
                message = f"{message} {reasons[0]}"
        job_services.mark_failed(job, error=message, result={"stage": "Import failed", **result})
        return result
    job_services.mark_completed(job, result={"stage": "Completed", **result})
    return result
