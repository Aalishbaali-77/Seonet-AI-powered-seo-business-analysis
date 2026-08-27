from __future__ import annotations

from django.utils import timezone

from apps.jobs import services as job_services
from apps.leads.models import Lead
from apps.leads.scoring import apply_lead_score, score_lead
from providers.leads.enrichment import (
    ApolloAdapter,
    ClearbitAdapter,
    HunterAdapter,
    WikidataAdapter,
    host_of,
    normalize_website,
    read_company_website,
)

FIELD_LIMITS = {
    "website": 200,
    "email": 254,
    "phone": 40,
    "location": 255,
    "industry": 160,
    "linkedin_url": 200,
    "description": 2000,
    "employee_count": 40,
}


def _fill(lead: Lead, field: str, value: str, source: str, applied: list[dict]) -> None:
    incoming = (value or "").strip()
    if field == "website":
        incoming = normalize_website(incoming)
    if not incoming or getattr(lead, field, ""):
        return
    setattr(lead, field, incoming[: FIELD_LIMITS.get(field, 255)])
    applied.append({"field": field, "source": source, "origin": "fact", "value": incoming[:80]})


def _name_match(left: str, right: str) -> bool:
    a = (left or "").strip().lower()
    b = (right or "").strip().lower()
    if not a or not b:
        return False
    return a == b or a in b or b in a


def _query_text(lead: Lead) -> str:
    name = (lead.company_name or "").strip()
    place = (lead.location or "").strip()
    if name and place and place.lower() not in name.lower():
        return f"{name} in {place}"
    return name


def _apply_record(lead: Lead, record: dict, source: str, applied: list[dict]) -> None:
    if not record:
        return
    if record.get("company_name") and not _name_match(lead.company_name, record.get("company_name") or ""):
        if not record.get("website") and not record.get("phone") and not record.get("email"):
            return
    for field in ("website", "email", "phone", "location", "industry", "linkedin_url", "description", "employee_count"):
        _fill(lead, field, str(record.get(field) or ""), source, applied)


def _from_discovery(lead: Lead, applied: list[dict], errors: list[str]) -> None:
    from apps.platform.lead_sources import resolve_lead_adapters
    from providers.leads.google_places import place_details

    text = _query_text(lead)
    if not text:
        return
    for adapter, api_key, source in resolve_lead_adapters():
        try:
            rows = adapter.search(query={"text": text}, api_key=api_key, limit=5)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{source.display_name}: {exc}")
            continue
        match = next((row for row in rows if _name_match(lead.company_name, row.get("company_name") or "")), rows[0] if rows else None)
        if not match:
            continue
        if source.provider == "google_places" and match.get("source_record_id") and (not lead.phone or not lead.website):
            details = place_details(str(match.get("source_record_id")), api_key)
            if details:
                match = {
                    **match,
                    "phone": details.get("international_phone_number") or details.get("formatted_phone_number") or match.get("phone") or "",
                    "website": details.get("website") or match.get("website") or "",
                    "location": details.get("formatted_address") or match.get("location") or "",
                }
        _apply_record(lead, match, source.code, applied)


def _from_serp(lead: Lead, applied: list[dict], errors: list[str]) -> None:
    if lead.website:
        return
    from apps.websites.serp import search_official_website

    query = f"{lead.company_name} official website"
    if lead.location:
        query = f"{lead.company_name} {lead.location} official website"
    try:
        url = search_official_website(query)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"licensed search: {exc}")
        return
    _fill(lead, "website", url, "licensed_search", applied)


def _from_website(lead: Lead, applied: list[dict], errors: list[str]) -> None:
    if not lead.website:
        return
    try:
        found = read_company_website(lead.website)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"website: {exc}")
        return
    _apply_record(lead, found, "website", applied)


def _from_wikidata(lead: Lead, applied: list[dict], errors: list[str]) -> None:
    from apps.platform.lead_sources import resolve_source_credentials

    source, key = resolve_source_credentials("wikidata")
    if source is None or not source.is_enabled:
        return
    try:
        _apply_record(lead, WikidataAdapter().lookup(company=lead.company_name, api_key=key), "wikidata", applied)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Wikidata: {exc}")


def _from_paid(lead: Lead, applied: list[dict], errors: list[str]) -> None:
    from apps.platform.lead_sources import resolve_source_credentials

    domain = host_of(lead.website) if lead.website else ""
    if not domain:
        return
    mapping = (("hunter", HunterAdapter), ("clearbit", ClearbitAdapter), ("apollo", ApolloAdapter))
    for code, adapter_cls in mapping:
        source, key = resolve_source_credentials(code)
        if source is None or not source.is_enabled:
            continue
        if source.requires_key and not key:
            continue
        try:
            row = adapter_cls().lookup(domain=domain, company=lead.company_name, api_key=key)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{source.display_name}: {exc}")
            continue
        _apply_record(lead, row, code, applied)


def enrich_lead(lead: Lead, *, user=None) -> dict:
    applied: list[dict] = []
    errors: list[str] = []
    _from_serp(lead, applied, errors)
    _from_wikidata(lead, applied, errors)
    _from_discovery(lead, applied, errors)
    _from_website(lead, applied, errors)
    _from_paid(lead, applied, errors)
    if applied:
        history = list(lead.enrichment or [])
        history.append({"at": timezone.now().isoformat(), "filled": applied, "errors": errors})
        lead.enrichment = history[-20:]
        lead.enriched_at = timezone.now()
        lead.save(
            update_fields=[
                "website",
                "email",
                "phone",
                "location",
                "industry",
                "linkedin_url",
                "description",
                "employee_count",
                "enrichment",
                "enriched_at",
                "updated_at",
            ]
        )
    icp = None
    if lead.search_id:
        icp = lead.search.icp
    apply_lead_score(lead, icp)
    payload = score_lead(lead, icp)
    from apps.auditlog.services import write_audit
    from apps.usage.services import record_usage

    record_usage(
        tenant=lead.tenant,
        user=user,
        event_type="lead_enriched",
        quantity=1,
        metadata={"filled": [item["field"] for item in applied], "errors": errors[:5]},
    )
    write_audit(
        action="LEAD_ENRICHED",
        tenant=lead.tenant,
        user=user,
        resource_type="lead",
        resource_id=lead.id,
        metadata={"filled": applied, "missing": payload["missing_fields"]},
    )
    return {
        "filled": applied,
        "missing_fields": payload["missing_fields"],
        "errors": errors,
        "sources": sorted({item["source"] for item in applied}),
        "why": (
            "Enrichment writes only values returned by the company website, Wikidata, enabled discovery APIs, "
            "or licensed search/enrichment keys. Empty contact fields stay empty."
        ),
    }


def start_bulk_enrich(*, tenant, user, lead_ids: list[str] | None = None) -> object:
    job = job_services.create_job(
        tenant=tenant,
        user=user,
        job_type="enrich_leads",
        payload={"lead_ids": [str(item) for item in (lead_ids or [])]},
    )
    job.celery_task_id = _enqueue_enrich_job(str(job.id))
    job.save(update_fields=["celery_task_id", "updated_at"])
    return job


def _enqueue_enrich_job(job_id: str) -> str:
    from threading import Thread

    from django.conf import settings
    from django.db import connections, transaction

    from workers.tasks import enrich_leads

    eager = getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False)
    propagate = getattr(settings, "CELERY_TASK_EAGER_PROPAGATES", False)
    if eager and not propagate:

        def runner() -> None:
            connections.close_all()
            enrich_leads(job_id)

        transaction.on_commit(lambda: Thread(target=runner, daemon=True, name=f"sipulse-enrich-{job_id}").start())
        return ""
    async_result = enrich_leads.delay(job_id)
    return async_result.id or ""


def execute_enrich_job(job) -> dict:
    ids = [str(item) for item in (job.payload or {}).get("lead_ids") or [] if str(item).strip()]
    qs = Lead.objects.for_tenant(job.tenant)
    if ids:
        qs = qs.filter(id__in=ids)
    else:
        from django.db.models import Q

        qs = qs.filter(Q(website="") | Q(email="") | Q(phone="") | Q(location="") | Q(industry=""))
    leads = list(qs.order_by("-created_at")[:50])
    job_services.mark_running(job, progress=8, result={"stage": f"Enriching {len(leads)} leads"})
    filled = 0
    errors: list[str] = []
    for index, lead in enumerate(leads, start=1):
        job_services.mark_progress(job, progress=10 + int((index / max(len(leads), 1)) * 80), result={"stage": f"Enriching {lead.company_name}"})
        try:
            result = enrich_lead(lead, user=job.user)
            if result["filled"]:
                filled += 1
            errors.extend(result.get("errors") or [])
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{lead.company_name}: {exc}")
    summary = {
        "enriched": filled,
        "attempted": len(leads),
        "errors": errors[:20],
        "why": "Only stored values returned by enabled sources were written. Missing contact fields were not invented.",
    }
    job_services.mark_completed(job, result=summary)
    return summary
