from __future__ import annotations

import re

from django.utils import timezone

from apps.jobs import services as job_services
from apps.leads.models import ICP, Lead, LeadSearch
from apps.usage.services import record_usage


def _heuristic_icp(text: str) -> dict:
    locations = re.findall(r"\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)\b", text)
    employees = ""
    match = re.search(r"(\d+)\s*\+?\s*employees", text, re.I)
    if match:
        employees = f"{match.group(1)}+"
    keywords = [part.strip() for part in re.split(r",| and ", text) if len(part.strip()) > 3][:8]
    industry = ""
    industry_match = re.search(r"to ([^,\.]+)", text, re.I)
    if industry_match:
        industry = industry_match.group(1).strip()[:160]
    return {
        "industry": industry,
        "employee_count": employees,
        "locations": list(dict.fromkeys(locations[:8])),
        "keywords": keywords,
        "origin": "heuristic",
    }


def _string_list(value) -> list[str]:
    if isinstance(value, str):
        items = [part.strip() for part in re.split(r",| and ", value) if part.strip()]
        return items[:8]
    if isinstance(value, list):
        return [str(item).strip()[:160] for item in value if str(item).strip()][:8]
    return []


def parse_icp_from_text(text: str, *, tenant=None, user=None) -> dict:
    heuristic = _heuristic_icp(text)
    if tenant is None:
        return heuristic
    from apps.common.exceptions import APIError
    from providers.ai.base import ProviderUnavailable
    from services.ai_gateway import AIService

    try:
        result = AIService.complete(
            tenant=tenant,
            user=user,
            task="icp_parse",
            prompt=(
                "Return JSON only with keys industry (string), employee_count (string), "
                "locations (array of strings), keywords (array of strings). "
                "Use only facts from the description. Use empty string or [] if unknown.\n\n"
                f"{text}"
            ),
            schema={"type": "object"},
        )
    except (ProviderUnavailable, APIError):
        return heuristic
    if not isinstance(result, dict) or ("industry" not in result and "locations" not in result and "keywords" not in result):
        return heuristic
    industry = str(result.get("industry") or heuristic["industry"])[:160]
    employees = str(result.get("employee_count") or heuristic["employee_count"])[:40]
    locations = _string_list(result.get("locations")) or heuristic["locations"]
    keywords = _string_list(result.get("keywords")) or heuristic["keywords"]
    return {
        "industry": industry,
        "employee_count": employees,
        "locations": locations,
        "keywords": keywords,
        "origin": "ai",
    }


def confirm_icp(icp: ICP) -> ICP:
    icp.status = ICP.Status.CONFIRMED
    icp.confirmed_at = timezone.now()
    icp.save(update_fields=["status", "confirmed_at", "updated_at"])
    return icp


def start_discovery(*, icp: ICP, user, geo_place=None) -> LeadSearch:
    if icp.status != ICP.Status.CONFIRMED:
        from apps.common.exceptions import APIError

        raise APIError("Confirm the ICP before starting discovery.", code="ICP_NOT_CONFIRMED", status_code=400)
    extra_locations = []
    if geo_place is not None:
        extra_locations.append(geo_place.name)
    elif not (icp.locations or []):
        from apps.markets.models import MarketFocus

        extra_locations = list(
            MarketFocus.objects.for_tenant(icp.tenant).select_related("place").values_list("place__name", flat=True)[:8]
        )
    locations = list(dict.fromkeys([*(icp.locations or []), *extra_locations]))
    job = job_services.create_job(
        tenant=icp.tenant,
        user=user,
        job_type="discover_leads",
        payload={"icp_id": str(icp.id), "extra_locations": extra_locations, "geo_place_id": str(geo_place.id) if geo_place else ""},
    )
    search = LeadSearch.objects.create(
        tenant=icp.tenant,
        icp=icp,
        job=job,
        status=LeadSearch.Status.QUEUED,
        zones=len(locations),
        queries=max(len(icp.keywords or []), 1),
    )
    job.celery_task_id = _enqueue_discovery_job(str(job.id))
    job.save(update_fields=["celery_task_id", "updated_at"])
    return search


def _enqueue_discovery_job(job_id: str) -> str:
    from threading import Thread

    from django.conf import settings
    from django.db import connections, transaction

    from workers.tasks import discover_leads

    eager = getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False)
    propagate = getattr(settings, "CELERY_TASK_EAGER_PROPAGATES", False)
    if eager and not propagate:
        def runner() -> None:
            connections.close_all()
            discover_leads(job_id)

        transaction.on_commit(lambda: Thread(target=runner, daemon=True, name=f"seonet-leads-{job_id}").start())
        return ""
    async_result = discover_leads.delay(job_id)
    return async_result.id or ""


def execute_discovery_job(job) -> LeadSearch:
    from apps.platform.lead_sources import build_icp_queries, resolve_lead_adapters
    from providers.ai.base import ProviderUnavailable

    search = LeadSearch.objects.select_related("icp").get(job=job)
    job_services.mark_running(job, progress=10, result={"stage": "Starting discovery"})
    search.status = LeadSearch.Status.RUNNING
    search.save(update_fields=["status", "updated_at"])
    adapters = resolve_lead_adapters()
    queries = build_icp_queries(search.icp)
    extra = [str(item).strip() for item in (job.payload or {}).get("extra_locations") or [] if str(item).strip()]
    if extra:
        seed = (search.icp.industry or search.icp.name or "business").strip()
        queries = list(dict.fromkeys([*queries, *[f"{seed} in {place}" for place in extra]]))[:8]
    search.queries = max(len(queries), 1)
    search.save(update_fields=["queries", "updated_at"])
    records: list[dict] = []
    errors: list[str] = []
    providers_used: list[str] = []
    try:
        if not adapters:
            records = []
        else:
            seen: set[str] = set()
            texts = queries or [search.icp.raw_input[:180]]
            total = max(len(texts) * len(adapters), 1)
            step = 0
            for adapter, api_key, source in adapters:
                providers_used.append(source.code)
                for text in texts:
                    step += 1
                    progress = 20 + int((step / total) * 60)
                    job_services.mark_progress(
                        job,
                        progress=progress,
                        result={"stage": f"Searching {source.display_name}: {text}"},
                    )
                    try:
                        rows = adapter.search(query={"text": text}, api_key=api_key)
                    except Exception as exc:  # noqa: BLE001
                        errors.append(f"{source.display_name}: {exc}")
                        continue
                    for row in rows:
                        source_id = f"{row.get('source')}:{row.get('source_record_id')}"
                        if not row.get("source_record_id") or source_id in seen:
                            continue
                        seen.add(source_id)
                        records.append(row)
    except Exception as exc:  # noqa: BLE001
        search.status = LeadSearch.Status.FAILED
        search.error = str(exc)
        search.save()
        job_services.mark_failed(job, error=str(exc), result={"providers": providers_used})
        raise ProviderUnavailable("Lead source provider temporarily unavailable. Retry scheduled.") from exc

    unique = 0
    from apps.integrations.push import push_lead

    for record in records:
        source_id = str(record.get("source_record_id") or record.get("company_name"))
        lead, created = Lead.objects.get_or_create(
            tenant=job.tenant,
            source=record.get("source", "none"),
            source_record_id=source_id,
            defaults={
                "search": search,
                "company_name": record.get("company_name", "Unknown"),
                "industry": record.get("industry", search.icp.industry),
                "location": record.get("location", ""),
                "website": record.get("website", ""),
                "phone": record.get("phone", ""),
                "email": record.get("email", ""),
                "origin": "fact",
            },
        )
        if created:
            unique += 1
            from apps.leads.scoring import apply_lead_score

            apply_lead_score(lead, search.icp)
            push_lead(job.tenant, lead, event="lead.created")
        else:
            changed = []
            for field in ("website", "phone", "email", "location", "industry"):
                incoming = str(record.get(field) or "").strip()
                if incoming and not getattr(lead, field):
                    setattr(lead, field, incoming)
                    changed.append(field)
            if changed:
                lead.save(update_fields=[*changed, "updated_at"])
    search.discovered = len(records)
    search.unique_count = unique
    search.duplicates = max(len(records) - unique, 0)
    search.status = LeadSearch.Status.COMPLETED
    search.error = "; ".join(errors)[:4000]
    search.save()
    record_usage(tenant=job.tenant, user=job.user, event_type="lead_discovered", quantity=unique, metadata={"search_id": str(search.id)})
    unavailable = ""
    if not adapters:
        unavailable = "Enable at least one lead discovery source in the platform console."
    elif not records and errors:
        unavailable = "; ".join(errors)
    if not records:
        job_services.mark_completed(
            job,
            result={
                "providers": providers_used,
                "message": unavailable or "No matching businesses were returned for this ICP.",
                "discovered": 0,
                "queries": queries,
                "errors": errors,
            },
        )
    else:
        job_services.mark_completed(
            job,
            result={"discovered": len(records), "unique": unique, "providers": providers_used, "queries": queries, "errors": errors},
        )
    return search
