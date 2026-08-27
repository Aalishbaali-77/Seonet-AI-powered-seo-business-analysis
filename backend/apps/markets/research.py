from __future__ import annotations

from apps.billing.entitlements import tenant_module_codes
from apps.business.analysis import commerce_analysis
from apps.business.models import BusinessProfile, CatalogProduct
from apps.common.exceptions import APIError
from apps.markets.catalog import ensure_geo_catalog
from apps.markets.models import GeoPlace, MarketSignal
from apps.markets.scoring import score_from_signals, tenant_weights
from apps.opportunities.models import Opportunity
from apps.websites.models import Website
from providers.ai.base import ProviderUnavailable
from services.ai_gateway import AIService

PROFILE_FIELDS = ("business_type", "industry", "category", "current_market", "goal", "notes")


def _citation(cid: str, kind: str, title: str, text: str, href: str) -> dict:
    return {"id": cid, "kind": kind, "title": title, "text": text, "href": href, "origin": "fact"}


def _profile_record(tenant) -> BusinessProfile:
    profile = BusinessProfile.objects.for_tenant(tenant).first()
    if profile is None:
        profile = BusinessProfile.objects.create(tenant=tenant)
    return profile


def profile_payload(tenant) -> dict:
    profile = _profile_record(tenant)
    return {
        "id": str(profile.id),
        "business_type": profile.business_type,
        "industry": profile.industry,
        "category": profile.category,
        "current_market": profile.current_market,
        "goal": profile.goal,
        "notes": profile.notes,
    }


def apply_profile_input(tenant, data: dict | None) -> dict:
    if not isinstance(data, dict):
        return profile_payload(tenant)
    profile = _profile_record(tenant)
    allowed_types = {choice[0] for choice in BusinessProfile.BusinessType.choices}
    updated: list[str] = []
    for key in PROFILE_FIELDS:
        if key not in data or data[key] is None:
            continue
        value = str(data[key]).strip()
        if key == "business_type":
            if value not in allowed_types:
                continue
            profile.business_type = value
        elif key in {"goal", "notes"}:
            setattr(profile, key, value[:4000])
        else:
            setattr(profile, key, value[:160])
        updated.append(key)
    if updated:
        profile.save(update_fields=[*updated, "updated_at"])
    return profile_payload(tenant)


def _has_business_input(profile: dict) -> bool:
    return bool(profile.get("industry") or profile.get("category") or profile.get("current_market") or profile.get("goal"))


def _profile_citations(profile: dict) -> list[dict]:
    citations: list[dict] = []
    href = "/app/markets"
    if _has_business_input(profile):
        subject = ", ".join(part for part in [profile.get("business_type"), profile.get("industry"), profile.get("category")] if part)
        market = profile.get("current_market") or ""
        text = f"FACT: this workspace business is {subject or 'saved'}."
        if market:
            text = f"{text[:-1]} Current market is {market}."
        citations.append(_citation("profile:business", "profile", "Business input", text, href))
    else:
        citations.append(
            _citation(
                "profile:missing",
                "profile",
                "Business input",
                "FACT: industry, category, current market, and goal are empty. Save them to analyze this tenant's business.",
                href,
            )
        )
    if profile.get("goal"):
        citations.append(_citation("profile:goal", "profile", "Goal", f"FACT: profile goal is {profile['goal']}.", href))
    return citations


def _product_citations(tenant) -> list[dict]:
    rows = list(CatalogProduct.objects.for_tenant(tenant).order_by("name")[:8])
    total = CatalogProduct.objects.for_tenant(tenant).count()
    if not total:
        return []
    names = ", ".join(item.name for item in rows if item.name)
    return [
        _citation(
            "products:catalog",
            "commerce",
            "Catalog",
            f"FACT: {total} catalog products are stored" + (f" including {names}." if names else "."),
            "/app/business/products",
        )
    ]


def collect_citations(tenant, profile: dict | None = None) -> list[dict]:
    profile = profile if profile is not None else profile_payload(tenant)
    citations = _profile_citations(profile) + _product_citations(tenant)
    analysis = commerce_analysis(tenant)
    demand = analysis.get("demand") or {}
    for row in demand.get("served") or []:
        city = row.get("city") or ""
        citations.append(
            _citation(
                f"served:{city}",
                "commerce",
                f"Serving {city}",
                row.get("why") or f"FACT: placed orders list {city}.",
                "/app/business/geography",
            )
        )
    for row in demand.get("thin") or []:
        city = row.get("city") or ""
        citations.append(
            _citation(
                f"thin:{city}",
                "commerce",
                f"Thin book in {city}",
                row.get("why") or "",
                "/app/business/geography",
            )
        )
    for row in demand.get("expansion") or []:
        city = row.get("city") or ""
        citations.append(
            _citation(
                f"expand:{city}",
                "commerce",
                f"Investigate serving {city}",
                row.get("why") or "",
                "/app/business/geography",
            )
        )
    ensure_geo_catalog()
    weights = tenant_weights(tenant)
    for place in GeoPlace.objects.filter(kind=GeoPlace.Kind.CITY, country_code="PK"):
        signals = list(MarketSignal.objects.for_tenant(tenant).filter(place=place))
        if not signals:
            continue
        payload = score_from_signals(signals, weights)
        citations.append(
            _citation(
                f"score:{place.code}",
                "signal",
                f"{place.name} market score",
                payload.get("why") or "",
                f"/app/markets/places/{place.id}",
            )
        )
        for item in signals[:4]:
            citations.append(
                _citation(
                    f"sig:{item.id}",
                    "signal",
                    f"{place.name} {item.kind}",
                    f"FACT: {place.name} {item.kind} is {item.value}/100 from {item.source} ({item.verification_status}).",
                    f"/app/markets/places/{place.id}",
                )
            )
    for item in Opportunity.objects.for_tenant(tenant).order_by("-created_at")[:8]:
        citations.append(
            _citation(
                f"opp:{item.id}",
                "opportunity",
                item.title,
                f"FACT: {item.title} ({item.type}, {item.status}). Evidence: {(item.evidence or '')[:240]}",
                f"/app/opportunities/{item.id}",
            )
        )
    for site in Website.objects.for_tenant(tenant).order_by("-updated_at")[:6]:
        citations.append(
            _citation(
                f"web:{site.id}",
                "website",
                site.name or site.domain,
                f"FACT: website {site.domain} is stored in this workspace.",
                "/app/websites",
            )
        )
    return citations[:60]


def market_findings(brief: dict) -> list[str]:
    findings: list[str] = []
    profile = brief.get("profile") or {}
    if _has_business_input(profile):
        subject = ", ".join(part for part in [profile.get("industry"), profile.get("category")] if part) or "this business"
        market = profile.get("current_market") or "an unspecified current market"
        findings.append(f"Analysis subject is {subject} in {market}.")
    else:
        findings.append("No industry, category, or current market is saved, so the analysis has no business subject yet.")
    served = brief.get("served") or []
    if served:
        findings.append("Served cities from placed orders: " + ", ".join(str(row.get("city")) for row in served[:8] if row.get("city")) + ".")
    elif brief.get("commerce_available") is False:
        findings.append("No placed orders, so served cities are empty.")
    expansion = brief.get("expansion") or []
    if expansion:
        findings.append("Expansion candidates with stored evidence: " + ", ".join(str(row.get("city")) for row in expansion[:8] if row.get("city")) + ".")
    overlap = brief.get("overlap") or []
    if overlap:
        findings.append("Cities already served that also have an ingested score: " + ", ".join(row["name"] for row in overlap[:8]) + ".")
    only_signal = brief.get("signal_without_orders") or []
    if only_signal:
        findings.append("Cities with an ingested score and zero placed orders: " + ", ".join(row["name"] for row in only_signal[:8]) + ".")
    if not brief.get("signal_count"):
        findings.append("No market signals ingested, so city opportunity scores stay empty.")
    return findings


def heuristic_recommendation(brief: dict) -> str:
    steps: list[str] = []
    profile = brief.get("profile") or {}
    if not _has_business_input(profile):
        steps.append("Save industry, category, current market, and goal as the business input.")
    if not brief.get("commerce_available"):
        steps.append("Import orders or sync a store so served cities exist.")
    if not brief.get("signal_count"):
        steps.append("Collect from market sources (Wikidata, OpenStreetMap, enabled lead APIs) or ingest a signals CSV.")
    overlap = brief.get("overlap") or []
    if overlap:
        steps.append("Deepen coverage in " + ", ".join(row["name"] for row in overlap[:4]) + " — those cities are already served and scored.")
    only_signal = brief.get("signal_without_orders") or []
    if only_signal:
        steps.append("Investigate serving " + ", ".join(row["name"] for row in only_signal[:4]) + " — scores exist and placed orders do not.")
    expansion = brief.get("expansion") or []
    if expansion:
        steps.append("Review expansion evidence for " + ", ".join(str(row.get("city")) for row in expansion[:4] if row.get("city")) + ".")
    if not steps:
        steps.append("Read served cities against ingested scores. No city grade is invented beyond those rows.")
    return " ".join(steps)


def _filter_citations(citations: list[dict], question: str) -> list[dict]:
    text = (question or "").strip().lower()
    if not text:
        return citations
    ensure_geo_catalog()
    mentioned = [place.name for place in GeoPlace.objects.filter(kind=GeoPlace.Kind.CITY, country_code="PK") if place.name.lower() in text]
    if not mentioned:
        return citations
    needles = [name.lower() for name in mentioned]
    kept = []
    for item in citations:
        blob = f"{item.get('title') or ''} {item.get('text') or ''}".lower()
        if item.get("kind") in {"profile", "commerce"} or any(name in blob for name in needles):
            kept.append(item)
    return kept or citations


def market_brief(tenant) -> dict:
    profile = profile_payload(tenant)
    analysis = commerce_analysis(tenant)
    demand = analysis.get("demand") or {}
    served = demand.get("served") or []
    expansion = demand.get("expansion") or []
    ensure_geo_catalog()
    weights = tenant_weights(tenant)
    scored = []
    unscored = 0
    for place in GeoPlace.objects.filter(kind=GeoPlace.Kind.CITY, country_code="PK").order_by("name"):
        payload = score_from_signals(MarketSignal.objects.for_tenant(tenant).filter(place=place), weights)
        if payload.get("score") is None:
            unscored += 1
            continue
        scored.append(
            {
                "id": str(place.id),
                "name": place.name,
                "code": place.code,
                "score": payload.get("score"),
                "origin": payload.get("origin"),
                "why": payload.get("why"),
                "coverage": payload.get("coverage"),
            }
        )
    scored.sort(key=lambda row: -(row["score"] or 0))
    served_names = {str(row.get("city") or "").strip().lower() for row in served if row.get("city")}
    overlap = [row for row in scored if row["name"].strip().lower() in served_names]
    signal_only = [row for row in scored if row["name"].strip().lower() not in served_names]
    citations = collect_citations(tenant, profile)
    brief = {
        "available": bool(served or scored or _has_business_input(profile)),
        "why": (
            "This analysis uses the tenant business profile as input, then cites stored commerce rows and ingested market signals. "
            "SIPulse does not license AlphaSense-style filings or invent city demand grades."
        ),
        "profile": profile,
        "subject": ", ".join(part for part in [profile.get("industry"), profile.get("category"), profile.get("current_market")] if part) or "",
        "served": served,
        "expansion": expansion,
        "scored": scored,
        "unscored_cities": unscored,
        "overlap": overlap,
        "signal_without_orders": signal_only,
        "signal_count": MarketSignal.objects.for_tenant(tenant).count(),
        "citations": citations,
        "commerce_available": bool(analysis.get("available")),
        "findings": [],
        "last_analysis": last_market_analysis(tenant),
    }
    brief["findings"] = market_findings(brief)
    return brief


MARKET_BRIEF_PROMPT = (
    "You are SIPulse Market Intelligence for this tenant's own business. "
    "Return JSON with keys inference and recommendation. "
    "Use only FACT citations, including the saved business profile. "
    "Analyze the market for that business (industry, category, current market, goal) plus served cities and ingested signals. "
    "Never invent filings, transcripts, revenue, conversion rates, or city grades. "
    "If the facts are insufficient, say so and name the missing input (profile, orders, or signals). "
    "Prefer where the workspace already serves versus cities that only have ingested signals."
)


def ask_market(*, tenant, user, question: str, profile: dict | None = None, on_progress=None) -> dict:
    def tick(progress: int, stage: str) -> None:
        if on_progress:
            on_progress(progress, stage)

    tick(8, "Reading business input")
    if profile:
        apply_profile_input(tenant, profile)
    tick(32, "Loading commerce facts")
    brief = market_brief(tenant)
    tick(58, "Scoring stored signals")
    citations = _filter_citations(brief.get("citations") or [], question)
    facts = [*(brief.get("findings") or []), *[item["text"] for item in citations if item.get("text")]]
    payload = {
        "question": question.strip(),
        "inference": "",
        "recommendation": heuristic_recommendation(brief),
        "origin": "facts_only",
        "citations": citations,
        "findings": brief.get("findings") or [],
        "brief": brief,
        "served_cities": len(brief.get("served") or []),
        "scored_cities": len(brief.get("scored") or []),
    }
    tick(78, "Drafting analysis")
    if "ai" not in tenant_module_codes(tenant):
        if payload["question"]:
            payload["recommendation"] = f"{payload['recommendation']} Enable the AI module for drafted inference."
        return payload
    try:
        asked = payload["question"] or "Analyze the market for this workspace business using only the FACT lines."
        result = AIService.complete(
            tenant=tenant,
            user=user,
            task="market_brief",
            prompt=MARKET_BRIEF_PROMPT + f"\nQuestion: {asked[:500]}",
            untrusted="\n".join(f"FACT: {line}" for line in facts) or "FACT: No business profile, commerce rows, or market signals are stored.",
            schema={"type": "object"},
        )
    except ProviderUnavailable:
        payload["recommendation"] = f"{payload['recommendation']} No AI provider is enabled."
        return payload
    except APIError as exc:
        if getattr(exc, "error_code", "") == "QUOTA_EXCEEDED":
            payload["recommendation"] = str(exc.detail)
            return payload
        raise
    if isinstance(result, dict):
        payload["inference"] = str(result.get("inference") or "")[:4000]
        payload["recommendation"] = str(result.get("recommendation") or payload["recommendation"])[:4000]
        payload["origin"] = "ai"
    return payload


def start_market_analysis(*, tenant, user, question: str = "", profile: dict | None = None):
    from apps.jobs import services as job_services

    job = job_services.create_job(
        tenant=tenant,
        user=user,
        job_type="analyze_market",
        payload={"question": question, "profile": profile or {}},
    )
    job.celery_task_id = _enqueue_analysis(str(job.id))
    job.save(update_fields=["celery_task_id", "updated_at"])
    job.refresh_from_db()
    return job


def _enqueue_analysis(job_id: str) -> str:
    from threading import Thread

    from django.conf import settings
    from django.db import connections, transaction

    from workers.tasks import analyze_market

    eager = getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False)
    propagate = getattr(settings, "CELERY_TASK_EAGER_PROPAGATES", False)
    if eager and not propagate:
        def runner() -> None:
            connections.close_all()
            analyze_market(job_id)

        transaction.on_commit(lambda: Thread(target=runner, daemon=True).start())
        return "thread"
    return str(analyze_market.delay(job_id).id)


def execute_market_analysis(job) -> dict:
    from apps.jobs import services as job_services

    payload = job.payload or {}
    job_services.mark_running(job, progress=5, result={"stage": "Reading business input"})

    def on_progress(progress: int, stage: str) -> None:
        job_services.mark_progress(job, progress=min(progress, 95), result={"stage": stage})

    try:
        result = ask_market(
            tenant=job.tenant,
            user=job.user,
            question=str(payload.get("question") or ""),
            profile=payload.get("profile") if isinstance(payload.get("profile"), dict) else None,
            on_progress=on_progress,
        )
    except Exception as exc:  # noqa: BLE001
        job_services.mark_failed(job, error=str(exc)[:4000], result={"stage": "Analysis failed"})
        return {"error": str(exc)[:4000]}
    stored = {
        "stage": "Completed",
        "question": result.get("question") or "",
        "findings": result.get("findings") or [],
        "inference": result.get("inference") or "",
        "recommendation": result.get("recommendation") or "",
        "origin": result.get("origin") or "facts_only",
        "served_cities": result.get("served_cities") or 0,
        "scored_cities": result.get("scored_cities") or 0,
        "citations": result.get("citations") or [],
        "citation_count": len(result.get("citations") or []),
    }
    job.payload = {}
    job.save(update_fields=["payload", "updated_at"])
    from apps.auditlog.services import write_audit

    write_audit(
        action="MARKET_ANALYZED",
        tenant=job.tenant,
        user=job.user,
        resource_type="market",
        metadata={"origin": stored.get("origin"), "question": str(stored.get("question") or "")[:400]},
    )
    job_services.mark_completed(job, result=stored)
    return stored


def last_market_analysis(tenant) -> dict | None:
    from apps.jobs.models import Job

    job = (
        Job.objects.for_tenant(tenant)
        .filter(job_type="analyze_market", status=Job.Status.COMPLETED)
        .order_by("-completed_at", "-updated_at")
        .first()
    )
    if job is None:
        return None
    result = job.result or {}
    if not (result.get("findings") or result.get("recommendation")):
        return None
    return {
        "question": result.get("question") or "",
        "findings": result.get("findings") or [],
        "inference": result.get("inference") or "",
        "recommendation": result.get("recommendation") or "",
        "origin": result.get("origin") or "facts_only",
        "citations": result.get("citations") or [],
    }
