from __future__ import annotations

import os

from apps.common.exceptions import APIError
from apps.platform.catalog import DEFAULT_LEAD_SOURCES
from apps.platform.models import LeadSource
from providers.ai.base import ProviderUnavailable
from providers.leads.registry import build_adapter

_CATALOG_FIELDS = ("provider", "category")


def ensure_lead_sources() -> None:
    for item in DEFAULT_LEAD_SOURCES:
        defaults = {
            "provider": item["provider"],
            "display_name": item["display_name"],
            "is_enabled": item["is_enabled"],
            "setup_hint": item["setup_hint"],
            "category": item["category"],
            "purpose": item["purpose"],
            "sort_order": item["sort_order"],
            "public_config": dict(item.get("public_config") or {}),
        }
        obj, created = LeadSource.objects.get_or_create(code=item["code"], defaults=defaults)
        if created:
            continue
        changed_fields: list[str] = []
        for field in _CATALOG_FIELDS:
            value = defaults[field]
            if getattr(obj, field) != value:
                setattr(obj, field, value)
                changed_fields.append(field)
        public = dict(obj.public_config or {})
        catalog_public = dict(defaults["public_config"] or {})
        merged = False
        for key, value in catalog_public.items():
            if public.get(key) in (None, "", [], {}):
                public[key] = value
                merged = True
        if merged:
            obj.public_config = public
            changed_fields.append("public_config")
        if changed_fields:
            obj.save(update_fields=[*changed_fields, "updated_at"])


def resolve_source_credentials(code: str) -> tuple[LeadSource | None, str]:
    ensure_lead_sources()
    source = LeadSource.objects.filter(code=code).first()
    if source is not None and not source.is_enabled:
        return source, ""
    key = ""
    env_names: list = []
    if source is not None:
        key = str((source.encrypted_config or {}).get("api_key") or (source.encrypted_config or {}).get("access_token") or "").strip()
        env_names = list((source.public_config or {}).get("env_keys") or [])
    if not key:
        for name in env_names:
            key = (os.getenv(str(name)) or "").strip()
            if key:
                break
    return source, key


def _source_key(source: LeadSource) -> str:
    key = str((source.encrypted_config or {}).get("api_key") or (source.encrypted_config or {}).get("access_token") or "").strip()
    if key:
        return key
    for name in (source.public_config or {}).get("env_keys") or []:
        key = (os.getenv(str(name)) or "").strip()
        if key:
            return key
    return ""


def build_icp_queries(icp) -> list[str]:
    locations = [str(item).strip() for item in (icp.locations or []) if str(item).strip()]
    keywords = [str(item).strip() for item in (icp.keywords or []) if str(item).strip()]
    industry = (icp.industry or "").strip()
    terms = keywords or ([industry] if industry else [])
    if not terms:
        raw = (icp.raw_input or icp.name or "").strip()
        if raw:
            terms = [raw[:180]]
    if not terms:
        return []
    queries: list[str] = []
    places = locations or [""]
    for term in terms[:4]:
        for place in places[:4]:
            if place and place.lower() not in term.lower():
                queries.append(f"{term} in {place}")
            else:
                queries.append(term)
    seen: list[str] = []
    for item in queries:
        if item and item not in seen:
            seen.append(item)
    return seen[:6]


def resolve_lead_adapters() -> list[tuple[object, str, LeadSource]]:
    ensure_lead_sources()
    adapters: list[tuple[object, str, LeadSource]] = []
    for source in LeadSource.objects.filter(category=LeadSource.Category.DISCOVERY, is_enabled=True).order_by("sort_order"):
        key = _source_key(source)
        if source.requires_key and not key:
            continue
        adapters.append((build_adapter(source), key, source))
    return adapters


def resolve_lead_adapter():
    adapters = resolve_lead_adapters()
    if not adapters:
        return None, "", "Enable at least one lead discovery source in the platform console and store its API credentials."
    adapter, key, source = adapters[0]
    return adapter, key, ""


def resolve_ai_adapters() -> list:
    from providers.ai.adapters import AnthropicAdapter, GeminiAdapter, OpenAIAdapter, XAIAdapter

    mapping = (
        ("openai", OpenAIAdapter),
        ("anthropic", AnthropicAdapter),
        ("xai", XAIAdapter),
        ("google_gemini", GeminiAdapter),
    )
    adapters = []
    for code, adapter_cls in mapping:
        source, key = resolve_source_credentials(code)
        if not key:
            continue
        adapters.append(adapter_cls(api_key=key, model=source.model if source else ""))
    return adapters


def test_lead_source(source: LeadSource) -> dict:
    key = _source_key(source)
    if source.requires_key and not key:
        raise APIError("Store an API key before testing this source.", code="VALIDATION_ERROR")
    if source.provider == LeadSource.Provider.GOOGLE_PAGESPEED:
        from apps.audits.browser_ux import probe_pagespeed

        return probe_pagespeed(key)
    if source.provider in {LeadSource.Provider.GOOGLE_CUSTOM_SEARCH, LeadSource.Provider.SERPAPI}:
        from apps.websites.serp import probe_serp

        from apps.websites.serp import _cse_id

        cx = _cse_id(str((source.public_config or {}).get("search_engine_id") or (source.public_config or {}).get("search_url") or ""))
        return probe_serp(source.provider, key, cx)
    if source.category == LeadSource.Category.ENRICHMENT:
        from providers.leads.enrichment import ApolloAdapter, ClearbitAdapter, HunterAdapter, WikidataAdapter

        probes = {
            LeadSource.Provider.HUNTER: HunterAdapter,
            LeadSource.Provider.CLEARBIT: ClearbitAdapter,
            LeadSource.Provider.APOLLO: ApolloAdapter,
            LeadSource.Provider.WIKIDATA: WikidataAdapter,
        }
        adapter_cls = probes.get(source.provider)
        if adapter_cls is None:
            raise APIError("This source cannot be tested yet.", code="VALIDATION_ERROR")
        return adapter_cls().probe(key)
    if source.category == LeadSource.Category.DISCOVERY:
        adapter = build_adapter(source)
        probe = getattr(adapter, "probe", None)
        if probe is None:
            rows = adapter.search(query={"text": "dentist in Karachi"}, api_key=key, limit=3)
            return {
                "ok": True,
                "sample_count": len(rows),
                "provider": adapter.name,
                "message": f"{source.display_name} returned {len(rows)} sample records.",
            }
        try:
            return probe(key)
        except ProviderUnavailable:
            raise
    from providers.ai.adapters import AnthropicAdapter, GeminiAdapter, OpenAIAdapter, XAIAdapter

    adapters = {
        LeadSource.Provider.OPENAI: OpenAIAdapter,
        LeadSource.Provider.ANTHROPIC: AnthropicAdapter,
        LeadSource.Provider.XAI: XAIAdapter,
        LeadSource.Provider.GOOGLE_GEMINI: GeminiAdapter,
    }
    adapter_cls = adapters.get(source.provider)
    if adapter_cls is None:
        raise APIError("This source cannot be tested yet.", code="VALIDATION_ERROR")
    probe = adapter_cls(api_key=key, model=source.model)
    try:
        return probe.probe()
    except ProviderUnavailable:
        raise
