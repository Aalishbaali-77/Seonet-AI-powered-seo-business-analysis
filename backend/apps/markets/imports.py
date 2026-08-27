from __future__ import annotations

import csv
import io
import re

from apps.common.exceptions import APIError
from apps.markets.catalog import ensure_geo_catalog
from apps.markets.models import GeoPlace, MarketSignal

CSV_COLUMNS = ["city", "kind", "value", "source", "source_url"]
KINDS = {choice[0] for choice in MarketSignal.Kind.choices}
MAX_CSV_BYTES = 2_000_000


def csv_template() -> tuple[str, str]:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(CSV_COLUMNS)
    return "sipulse-market-signals-template.csv", "\ufeff" + buf.getvalue()


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
    cleaned = (value or "").replace("\ufeff", "").strip().strip('"').lower()
    return re.sub(r"[\s\-/]+", "_", cleaned)


def _sniff(sample: str) -> str:
    header = next((line for line in sample.splitlines() if line.strip()), "")
    counts = {";": header.count(";"), "\t": header.count("\t"), ",": header.count(",")}
    best = max(counts, key=lambda key: counts[key])
    return best if counts[best] else ","


def _place(city: str) -> GeoPlace | None:
    needle = (city or "").strip()
    if not needle:
        return None
    ensure_geo_catalog()
    return (
        GeoPlace.objects.filter(kind=GeoPlace.Kind.CITY, country_code="PK", name__iexact=needle).first()
        or GeoPlace.objects.filter(kind=GeoPlace.Kind.CITY, country_code="PK", code__iexact=needle).first()
    )


def import_signals_csv(tenant, text: str, *, on_progress=None) -> dict:
    delimiter = _sniff(text)
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    try:
        headers = [_normalize_header(item) for item in next(reader)]
    except StopIteration:
        return {"created": 0, "skipped": 0, "kind": "signals", "skip_reasons": ["The file has no header row."]}
    aliases = {"place": "city", "place_name": "city", "signal": "kind", "score": "value"}
    headers = [aliases.get(item, item) for item in headers]
    created = 0
    skipped = 0
    reasons: list[str] = []
    rows = [row for row in reader if any(str(cell).strip() for cell in row)]
    total = len(rows)
    for index, raw in enumerate(rows, start=1):
        mapped = {headers[i]: str(raw[i]).strip() if i < len(raw) else "" for i in range(len(headers))}
        city = mapped.get("city") or ""
        kind = (mapped.get("kind") or "").lower().replace(" ", "_")
        source = mapped.get("source") or ""
        try:
            value = int(float(str(mapped.get("value") or "0").replace(",", ".")))
        except ValueError:
            value = -1
        place = _place(city)
        if place is None or kind not in KINDS or not source or value < 0 or value > 100:
            skipped += 1
            if len(reasons) < 8:
                reasons.append(f"Row {index}: need a known city, kind, value 0-100, and source.")
            continue
        MarketSignal.objects.create(
            tenant=tenant,
            place=place,
            kind=kind,
            value=value,
            source=source[:120],
            source_url=(mapped.get("source_url") or "")[:200],
            verification_status=MarketSignal.Verification.UNVERIFIED,
        )
        created += 1
        if on_progress:
            on_progress(index, total)
    return {"created": created, "skipped": skipped, "kind": "signals", "skip_reasons": reasons}


def start_signal_import(*, tenant, user, raw: bytes):
    from apps.jobs import services as job_services

    if not raw:
        raise APIError("The CSV file is empty.", code="VALIDATION_ERROR")
    if len(raw) > MAX_CSV_BYTES:
        raise APIError("CSV is larger than 2 MB.", code="VALIDATION_ERROR")
    job = job_services.create_job(
        tenant=tenant,
        user=user,
        job_type="import_markets",
        payload={"csv_text": decode_csv_bytes(raw)},
    )
    job.celery_task_id = _enqueue(str(job.id))
    job.save(update_fields=["celery_task_id", "updated_at"])
    job.refresh_from_db()
    return job


def _enqueue(job_id: str) -> str:
    from threading import Thread

    from django.conf import settings
    from django.db import connections, transaction

    from workers.tasks import import_markets

    eager = getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False)
    propagate = getattr(settings, "CELERY_TASK_EAGER_PROPAGATES", False)
    if eager and not propagate:
        def runner() -> None:
            connections.close_all()
            import_markets(job_id)

        transaction.on_commit(lambda: Thread(target=runner, daemon=True).start())
        return "thread"
    return str(import_markets.delay(job_id).id)


def execute_signal_import(job) -> dict:
    from apps.auditlog.services import write_audit
    from apps.jobs import services as job_services
    from apps.usage.services import record_usage

    text = (job.payload or {}).get("csv_text") or ""
    job.payload = {}
    job.save(update_fields=["payload", "updated_at"])
    job_services.mark_running(job, progress=10, result={"stage": "Reading file"})

    def on_progress(done: int, total: int) -> None:
        if done == total or done % 10 == 0:
            job_services.mark_progress(
                job,
                progress=15 + int((done / max(total, 1)) * 80),
                result={"stage": "Importing rows", "processed": done, "total": total},
            )

    result = import_signals_csv(job.tenant, text, on_progress=on_progress)
    record_usage(tenant=job.tenant, user=job.user, event_type="market_signals_imported", quantity=int(result.get("created") or 0))
    write_audit(
        action="MARKET_SIGNALS_IMPORTED",
        tenant=job.tenant,
        user=job.user,
        resource_type="market",
        metadata={"created": result.get("created"), "skipped": result.get("skipped")},
    )
    if int(result.get("created") or 0) == 0:
        message = (result.get("skip_reasons") or ["No signal rows could be imported."])[0]
        job_services.mark_failed(job, error=message, result={"stage": "Import failed", **result})
        return result
    job_services.mark_completed(job, result={"stage": "Completed", **result})
    return result
