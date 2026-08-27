from __future__ import annotations

from apps.audits.models import Audit
from apps.business.models import CatalogProduct, CommerceOrder
from apps.crm.models import Deal
from apps.leads.models import Lead, LeadList
from apps.marketing.models import Campaign
from apps.markets.catalog import ensure_geo_catalog
from apps.markets.models import GeoPlace, MarketSignal
from apps.markets.scoring import score_from_signals, tenant_weights
from apps.opportunities.models import Opportunity
from apps.websites.models import Website

INTENTS = (
    "count_leads",
    "count_qualified_leads",
    "count_orders",
    "count_products",
    "count_opportunities",
    "count_campaigns",
    "count_websites",
    "count_crm_deals",
    "scored_cities",
    "lead_list_sizes",
    "market_analysis",
)

FORECAST_MARKERS = ("next year", "will revenue", "forecast", "predict conversion", "open rate")
MARKET_MARKERS = (
    "market",
    "city",
    "cities",
    "where should we",
    "where do we sell",
    "where do i sell",
    "expand",
    "demand",
    "competition",
    "served",
    "analyse",
    "analyze",
    "what should we sell",
    "which city",
    "current market",
    "industry",
)


def _wants_count(text: str) -> bool:
    return "how many" in text or "count" in text or "number of" in text or "list" in text


def _match_intent(question: str) -> str | None:
    text = (question or "").lower()
    if not text.strip():
        return None
    if any(marker in text for marker in FORECAST_MARKERS):
        return None
    if "qualified" in text and "lead" in text:
        return "count_qualified_leads"
    if "lead list" in text or ("list" in text and "lead" in text):
        return "lead_list_sizes"
    if "scored" in text and "city" in text:
        return "scored_cities"
    if _wants_count(text):
        if "deal" in text or "crm" in text:
            return "count_crm_deals"
        if "campaign" in text:
            return "count_campaigns"
        if "opportunit" in text:
            return "count_opportunities"
        if "order" in text or "revenue" in text:
            return "count_orders"
        if "product" in text:
            return "count_products"
        if "website" in text or "audit" in text:
            return "count_websites"
        if "lead" in text:
            return "count_leads"
        if "city" in text or "market" in text or "served" in text:
            return "market_analysis"
        return None
    if any(marker in text for marker in MARKET_MARKERS):
        return "market_analysis"
    return None


def _facts(tenant, intent: str) -> list[str]:
    if intent == "count_leads":
        return [f"{Lead.objects.for_tenant(tenant).count()} leads are stored in this workspace."]
    if intent == "count_qualified_leads":
        return [f"{Lead.objects.for_tenant(tenant).filter(status=Lead.Status.QUALIFIED).count()} leads have status qualified."]
    if intent == "count_orders":
        return [f"{CommerceOrder.objects.for_tenant(tenant).count()} commerce orders have been imported or synced."]
    if intent == "count_products":
        return [f"{CatalogProduct.objects.for_tenant(tenant).count()} catalog products have been imported or synced."]
    if intent == "count_opportunities":
        return [f"{Opportunity.objects.for_tenant(tenant).count()} growth opportunities are recorded."]
    if intent == "count_campaigns":
        return [f"{Campaign.objects.for_tenant(tenant).count()} marketing campaigns are recorded."]
    if intent == "count_websites":
        completed = Audit.objects.for_tenant(tenant).filter(status=Audit.Status.COMPLETED).count()
        return [
            f"{Website.objects.for_tenant(tenant).count()} websites are connected.",
            f"{completed} audits are completed.",
        ]
    if intent == "count_crm_deals":
        return [f"{Deal.objects.for_tenant(tenant).count()} native CRM deals exist."]
    if intent == "scored_cities":
        ensure_geo_catalog()
        weights = tenant_weights(tenant)
        scored = 0
        for city in GeoPlace.objects.filter(kind=GeoPlace.Kind.CITY, country_code="PK"):
            payload = score_from_signals(MarketSignal.objects.for_tenant(tenant).filter(place=city), weights)
            if payload.get("score") is not None:
                scored += 1
        return [f"{scored} cities have ingested market signals and a computed score."]
    if intent == "lead_list_sizes":
        rows = LeadList.objects.for_tenant(tenant)
        if not rows:
            return ["No saved lead lists exist."]
        return [f"List {item.name} has {Lead.objects.for_tenant(tenant).filter(lists=item).count()} leads." for item in rows[:12]]
    return []


def _market_analysis_payload(*, tenant, user, question: str) -> dict:
    from apps.billing.entitlements import tenant_module_codes
    from apps.jobs.models import Job
    from apps.markets.research import start_market_analysis

    if "markets" not in tenant_module_codes(tenant):
        return {
            "question": question,
            "intent": None,
            "facts": [],
            "origin": "none",
            "why": "Market analysis needs the Market Intelligence module on this package.",
        }
    job = start_market_analysis(tenant=tenant, user=user, question=question)
    job.refresh_from_db()
    result = job.result or {}
    facts = list(result.get("findings") or [])
    for item in result.get("citations") or []:
        text = item.get("text") or ""
        if text and text not in facts:
            facts.append(text)
    running = job.status not in {Job.Status.COMPLETED, Job.Status.FAILED}
    return {
        "question": question,
        "intent": "market_analysis",
        "facts": facts[:24],
        "inference": result.get("inference") or "",
        "recommendation": result.get("recommendation") or "",
        "citations": result.get("citations") or [],
        "origin": result.get("origin") or ("queued" if running else "facts_only"),
        "why": (
            "Analysis is running. Progress is live from the workspace job."
            if running
            else "Market analysis for this workspace business from the saved profile, placed orders, and ingested signals. City grades are not invented."
        ),
        "href": "/app/markets",
        "job_id": str(job.id),
    }


def record_ask(*, tenant, user, payload: dict) -> None:
    from apps.ai.capture import QUESTION_LIMIT, clip
    from apps.ai.models import AskQuery
    from apps.auditlog.services import write_audit

    AskQuery.objects.create(
        tenant=tenant,
        user=user if getattr(user, "pk", None) else None,
        question=clip(payload.get("question") or "", QUESTION_LIMIT),
        intent=str(payload.get("intent") or "")[:80],
        origin=str(payload.get("origin") or "")[:40],
        facts=list(payload.get("facts") or [])[:20],
        why=clip(payload.get("why") or "", 500),
    )
    write_audit(
        action="ASK_QUESTION",
        tenant=tenant,
        user=user,
        resource_type="ask",
        metadata={"intent": payload.get("intent"), "origin": payload.get("origin"), "question": clip(payload.get("question") or "", 400)},
    )


def answer_question(*, tenant, user, question: str) -> dict:
    intent = _match_intent(question)
    origin = "query"
    if intent is None:
        from apps.billing.entitlements import tenant_module_codes
        from apps.common.exceptions import APIError
        from providers.ai.base import ProviderUnavailable
        from services.ai_gateway import AIService

        if "ai" in tenant_module_codes(tenant):
            try:
                result = AIService.complete(
                    tenant=tenant,
                    user=user,
                    task="nl_query",
                    prompt=(
                        "Map the user question to one intent from this allowlist: "
                        + ", ".join(INTENTS)
                        + ". Return JSON {intent: string}. If it cannot be answered from Seonet counts, intent must be empty."
                    ),
                    untrusted=question,
                    schema={"type": "object"},
                )
                candidate = str((result or {}).get("intent") or "")
                if candidate in INTENTS:
                    intent = candidate
                    origin = "ai_query"
            except (ProviderUnavailable, APIError):
                intent = None
    if intent is None:
        payload = {
            "question": question,
            "intent": None,
            "facts": [],
            "origin": "none",
            "why": "This question is not mapped to a Seonet count, list, or market analysis. Raw SQL is not allowed, and numbers are not invented.",
        }
        record_ask(tenant=tenant, user=user, payload=payload)
        return payload
    if intent == "market_analysis":
        payload = _market_analysis_payload(tenant=tenant, user=user, question=question)
        record_ask(tenant=tenant, user=user, payload=payload)
        return payload
    payload = {
        "question": question,
        "intent": intent,
        "facts": _facts(tenant, intent),
        "origin": origin,
        "why": "Answered from workspace rows via an allowlisted query. Not a chatbot estimate.",
    }
    record_ask(tenant=tenant, user=user, payload=payload)
    return payload
