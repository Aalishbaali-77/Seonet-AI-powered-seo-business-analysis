from __future__ import annotations

import os
import time
from urllib.parse import quote

import httpx
from django.utils import timezone

from apps.business.models import BusinessProfile, CatalogProduct
from apps.markets.catalog import ensure_geo_catalog
from apps.markets.models import GeoPlace, MarketSignal
from providers.ai.base import ProviderUnavailable

USER_AGENT = "SIPulseBot/1.0 (market-collect; +https://sipulse.local)"
OVERPASS_URLS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)
WIKIDATA_URL = "https://query.wikidata.org/sparql"
WIKIDATA_CITIES = {
    "PK-SD-KHI": "Q8660",
    "PK-SD-HYD": "Q1643125",
    "PK-PB-LHE": "Q11739",
    "PK-PB-FSD": "Q173985",
    "PK-PB-RWP": "Q93305",
    "PK-PB-MUX": "Q93180",
    "PK-IS-ISB": "Q1362",
    "PK-KP-PEW": "Q1113426",
    "PK-BA-UET": "Q1850",
}
HEALTHCARE_MARKERS = ("health", "hospital", "clinic", "pharma", "medical", "npi", "doctor")


def _testing() -> bool:
    return bool(os.environ.get("PYTEST_CURRENT_TEST"))


def _get_json(url: str, *, params: dict | None = None, headers: dict | None = None, timeout: int = 30, data: str | None = None):
    merged = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    merged.update(headers or {})
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        if data is not None:
            response = client.post(url, content=data, headers=merged)
        else:
            response = client.get(url, params=params, headers=merged)
    if response.status_code >= 400:
        raise ProviderUnavailable(f"{url} returned HTTP {response.status_code}.")
    try:
        return response.json()
    except Exception as exc:  # noqa: BLE001
        raise ProviderUnavailable("Provider returned a non-JSON response.") from exc


def search_term(tenant) -> str:
    profile = BusinessProfile.objects.for_tenant(tenant).first()
    product = CatalogProduct.objects.for_tenant(tenant).exclude(category="").order_by("name").first()
    for value in (
        (profile.category if profile else "") or "",
        (profile.industry if profile else "") or "",
        (product.category if product else "") or "",
        (product.name if product else "") or "",
    ):
        cleaned = value.strip()
        if cleaned:
            return cleaned[:80]
    if profile and profile.business_type == BusinessProfile.BusinessType.SERVICES:
        return "office"
    return "shop"


def catalog_cities():
    ensure_geo_catalog()
    return list(GeoPlace.objects.filter(kind=GeoPlace.Kind.CITY, country_code="PK").order_by("name"))


def _relative(pairs: list[tuple[GeoPlace, int]]) -> list[tuple[GeoPlace, int, int]]:
    positive = [(place, count) for place, count in pairs if count > 0]
    if not positive:
        return []
    peak = max(count for _, count in positive)
    return [(place, count, int(round(100 * count / peak))) for place, count in positive]


def _upsert(*, tenant, place, kind: str, value: int, source: str, source_provider: str, source_url: str = "") -> bool:
    qs = MarketSignal.objects.for_tenant(tenant).filter(place=place, kind=kind, source_provider=source_provider)
    now = timezone.now()
    current = qs.order_by("-updated_at").first()
    if current is None:
        MarketSignal.objects.create(
            tenant=tenant,
            place=place,
            kind=kind,
            value=max(0, min(100, value)),
            source=source[:120],
            source_url=source_url[:200],
            source_provider=source_provider[:80],
            retrieved_at=now,
            verification_status=MarketSignal.Verification.ESTIMATED,
        )
        return True
    current.value = max(0, min(100, value))
    current.source = source[:120]
    current.source_url = source_url[:200]
    current.retrieved_at = now
    current.verification_status = MarketSignal.Verification.ESTIMATED
    current.save(update_fields=["value", "source", "source_url", "retrieved_at", "verification_status", "updated_at"])
    qs.exclude(id=current.id).delete()
    return False


def collect_wikidata_population() -> list[tuple[GeoPlace, int]]:
    cities = [place for place in catalog_cities() if place.code in WIKIDATA_CITIES]
    if not cities:
        return []
    values = " ".join(f"wd:{WIKIDATA_CITIES[place.code]}" for place in cities)
    query = (
        "SELECT ?id ?pop WHERE { VALUES ?id { "
        + values
        + " } ?id wdt:P1082 ?pop. }"
    )
    payload = _get_json(
        WIKIDATA_URL,
        params={"query": query, "format": "json"},
        headers={"Accept": "application/sparql-results+json", "User-Agent": USER_AGENT},
        timeout=40,
    )
    by_qid: dict[str, int] = {}
    for row in ((payload.get("results") or {}).get("bindings") or []):
        ident = str((row.get("id") or {}).get("value") or "")
        qid = ident.rsplit("/", 1)[-1]
        try:
            by_qid[qid] = int(float((row.get("pop") or {}).get("value") or 0))
        except (TypeError, ValueError):
            continue
    found: list[tuple[GeoPlace, int]] = []
    for place in cities:
        count = by_qid.get(WIKIDATA_CITIES[place.code]) or 0
        if count:
            found.append((place, count))
    return found


def _overpass_count(city_name: str, shop_filter: str) -> int:
    query = (
        f'[out:json][timeout:25];'
        f'area["name"="{city_name}"]["boundary"="administrative"]->.a;'
        f'(node[{shop_filter}](area.a); way[{shop_filter}](area.a););'
        f'out count;'
    )
    last_error = None
    for url in OVERPASS_URLS:
        try:
            payload = _get_json(
                url,
                data=f"data={quote(query)}",
                headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": USER_AGENT},
                timeout=40,
            )
            elements = payload.get("elements") or []
            if not elements:
                return 0
            tags = elements[0].get("tags") or {}
            return int(float(tags.get("total") or tags.get("nodes") or 0))
        except (ProviderUnavailable, TypeError, ValueError, httpx.HTTPError) as exc:
            last_error = exc
            continue
    if last_error:
        raise last_error
    return 0


def collect_overpass_shops(term: str) -> list[tuple[GeoPlace, int]]:
    shop_filter = 'shop'
    lowered = term.lower()
    if any(word in lowered for word in ("chocolate", "sweet", "confection", "gift")):
        shop_filter = 'shop~"chocolate|confectionery|gift|convenience|supermarket"'
    elif any(word in lowered for word in ("cloth", "apparel", "fashion")):
        shop_filter = 'shop~"clothes|fashion|boutique"'
    rows: list[tuple[GeoPlace, int]] = []
    for place in catalog_cities():
        try:
            count = _overpass_count(place.name, shop_filter)
        except (ProviderUnavailable, httpx.HTTPError):
            continue
        if count:
            rows.append((place, count))
        if not _testing():
            time.sleep(1.0)
    return rows


def collect_adapter_counts(tenant, term: str) -> dict[str, list[tuple[GeoPlace, int]]]:
    from apps.platform.lead_sources import resolve_lead_adapters

    grouped: dict[str, list[tuple[GeoPlace, int]]] = {}
    adapters = resolve_lead_adapters()
    for adapter, api_key, source in adapters:
        if source.code == "npi_registry" and not any(marker in term.lower() for marker in HEALTHCARE_MARKERS):
            continue
        counts: list[tuple[GeoPlace, int]] = []
        for place in catalog_cities():
            try:
                records = adapter.search(query={"text": f"{term} in {place.name}"}, api_key=api_key, limit=20) or []
            except ProviderUnavailable:
                continue
            if records:
                counts.append((place, len(records)))
            if source.code == "openstreetmap" and not _testing():
                time.sleep(1.1)
        if counts:
            grouped[source.code] = counts
    return grouped


def collect_market_signals(tenant) -> dict:
    term = search_term(tenant)
    created = 0
    updated = 0
    errors: list[str] = []
    sources_used: list[str] = []

    try:
        population = _relative(collect_wikidata_population())
        if population:
            sources_used.append("wikidata")
        for place, count, value in population:
            is_new = _upsert(
                tenant=tenant,
                place=place,
                kind=MarketSignal.Kind.POPULATION,
                value=value,
                source=f"Wikidata population {count} (relative among catalog cities with a retrieved figure)",
                source_provider="wikidata",
                source_url="https://query.wikidata.org/",
            )
            created += int(is_new)
            updated += int(not is_new)
    except (ProviderUnavailable, httpx.HTTPError) as exc:
        errors.append(f"Wikidata: {exc}")

    try:
        shops = _relative(collect_overpass_shops(term))
        if shops:
            sources_used.append("overpass")
        for place, count, value in shops:
            is_new = _upsert(
                tenant=tenant,
                place=place,
                kind=MarketSignal.Kind.BUSINESS_DENSITY,
                value=value,
                source=f"OpenStreetMap Overpass shop count {count} for {term}",
                source_provider="overpass",
                source_url="https://overpass-api.de/",
            )
            created += int(is_new)
            updated += int(not is_new)
    except (ProviderUnavailable, httpx.HTTPError) as exc:
        errors.append(f"Overpass: {exc}")

    for code, pairs in collect_adapter_counts(tenant, term).items():
        scaled = _relative(pairs)
        if not scaled:
            continue
        sources_used.append(code)
        for place, count, value in scaled:
            is_new = _upsert(
                tenant=tenant,
                place=place,
                kind=MarketSignal.Kind.BUSINESS_DENSITY,
                value=value,
                source=f"{code} listed {count} matches for '{term} in {place.name}' (sample, not a census)",
                source_provider=code,
            )
            created += int(is_new)
            updated += int(not is_new)

    return {
        "created": created,
        "updated": updated,
        "term": term,
        "sources": sources_used,
        "errors": errors[:8],
        "kind": "collect",
    }


def start_market_collect(*, tenant, user):
    from apps.jobs import services as job_services

    job = job_services.create_job(tenant=tenant, user=user, job_type="collect_markets", payload={"term": search_term(tenant)})
    job.celery_task_id = _enqueue(str(job.id))
    job.save(update_fields=["celery_task_id", "updated_at"])
    job.refresh_from_db()
    return job


def _enqueue(job_id: str) -> str:
    from threading import Thread

    from django.conf import settings
    from django.db import connections, transaction

    from workers.tasks import collect_markets

    eager = getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False)
    propagate = getattr(settings, "CELERY_TASK_EAGER_PROPAGATES", False)
    if eager and not propagate:
        def runner() -> None:
            connections.close_all()
            collect_markets(job_id)

        transaction.on_commit(lambda: Thread(target=runner, daemon=True).start())
        return "thread"
    return str(collect_markets.delay(job_id).id)


def execute_market_collect(job) -> dict:
    from apps.auditlog.services import write_audit
    from apps.jobs import services as job_services
    from apps.usage.services import record_usage

    job_services.mark_running(job, progress=8, result={"stage": "Reading business input"})
    job_services.mark_progress(job, progress=20, result={"stage": "Querying open market data"})
    result = collect_market_signals(job.tenant)
    job_services.mark_progress(job, progress=80, result={"stage": "Storing estimated signals", **result})
    record_usage(tenant=job.tenant, user=job.user, event_type="market_signals_collected", quantity=int(result.get("created") or 0) + int(result.get("updated") or 0))
    write_audit(
        action="MARKET_SIGNALS_COLLECTED",
        tenant=job.tenant,
        user=job.user,
        resource_type="market",
        metadata={"created": result.get("created"), "updated": result.get("updated"), "sources": result.get("sources")},
    )
    stored = int(result.get("created") or 0) + int(result.get("updated") or 0)
    if stored == 0:
        message = (result.get("errors") or ["No enabled lead source or open-data API returned listings for catalog cities."])[0]
        job_services.mark_failed(job, error=str(message)[:4000], result={"stage": "Collect failed", **result})
        return result
    job_services.mark_completed(job, result={"stage": "Completed", **result})
    return result
