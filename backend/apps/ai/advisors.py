from __future__ import annotations

from apps.billing.entitlements import tenant_module_codes
from apps.business.analysis import analysis_facts, commerce_analysis
from apps.business.models import BusinessProfile
from apps.leads.models import Lead
from apps.opportunities.models import Opportunity
from apps.common.exceptions import APIError
from providers.ai.base import ProviderUnavailable
from services.ai_gateway import AIService

DOMAINS = {"business", "market", "opportunity", "lead", "marketing"}


def _profile(tenant) -> dict:
    profile = BusinessProfile.objects.for_tenant(tenant).first()
    if profile is None:
        return {}
    return {
        "industry": profile.industry,
        "category": profile.category,
        "current_market": profile.current_market,
        "business_type": profile.business_type,
        "goal": profile.goal,
    }


def gather_facts(tenant, domain: str) -> list[str]:
    facts: list[str] = []
    if domain == "business":
        facts.extend(analysis_facts(commerce_analysis(tenant)))
        profile = _profile(tenant)
        if profile.get("goal"):
            facts.append(f"Profile goal is {profile['goal']}.")
        if profile.get("business_type"):
            facts.append(f"Business type is {profile['business_type']}.")
    elif domain == "market":
        from apps.markets.research import market_brief

        brief = market_brief(tenant)
        facts.append(f"{brief.get('signal_count') or 0} market signals are ingested in this workspace.")
        facts.append(f"{len(brief.get('scored') or [])} cities have a computed score. {brief.get('unscored_cities') or 0} catalog cities have no signals.")
        for row in (brief.get("served") or [])[:8]:
            facts.append(row.get("why") or f"FACT: placed orders list {row.get('city')}.")
        for row in (brief.get("overlap") or [])[:8]:
            facts.append(f"FACT: {row.get('name')} is both a served city and has an ingested score {row.get('score')}/100.")
        for row in (brief.get("signal_without_orders") or [])[:8]:
            facts.append(f"FACT: {row.get('name')} has an ingested score {row.get('score')}/100 and 0 placed orders.")
        facts.append("Pakistan geography is reference data, not demand. Scores are not invented.")
    elif domain == "opportunity":
        rows = Opportunity.objects.for_tenant(tenant).order_by("-created_at")[:12]
        if not rows:
            facts.append("No growth opportunities have been recorded.")
        for item in rows:
            facts.append(f"{item.title} ({item.type}, {item.status}, origin {item.origin}).")
    elif domain == "lead":
        leads = Lead.objects.for_tenant(tenant)
        facts.append(f"{leads.count()} leads in this workspace.")
        facts.append(f"{leads.filter(status=Lead.Status.QUALIFIED).count()} qualified.")
        scored = leads.exclude(lead_score=None).count()
        facts.append(f"{scored} leads have a completeness/ICP score.")
        facts.append("Lead scores are not market grades and are not invented contact data.")
    elif domain == "marketing":
        from apps.marketing.models import Campaign

        rows = Campaign.objects.for_tenant(tenant)
        facts.append(f"{rows.count()} campaigns are recorded.")
        facts.append(f"{rows.filter(status=Campaign.Status.SENT).count()} are marked sent.")
        facts.append("Sent means a recorded send to an existing audience. SIPulse does not dispatch email.")
    return facts


def advise(*, tenant, user, domain: str) -> dict:
    if domain not in DOMAINS:
        from apps.common.exceptions import APIError

        raise APIError("Unknown advisor domain.", code="VALIDATION_ERROR")
    facts = gather_facts(tenant, domain)
    payload = {
        "domain": domain,
        "facts": facts,
        "inference": "",
        "recommendation": "",
        "origin": "facts_only",
    }
    if "ai" not in tenant_module_codes(tenant):
        payload["recommendation"] = "Enable the AI module to generate INFERENCE and RECOMMENDATION from these facts."
        return payload
    prompt = BUSINESS_EXPERT_PROMPT if domain == "business" else GENERIC_ADVISOR_PROMPT
    try:
        result = AIService.complete(
            tenant=tenant,
            user=user,
            task=f"{domain}_advisor",
            prompt=prompt,
            untrusted="\n".join(f"FACT: {line}" for line in facts),
            schema={"type": "object"},
        )
    except ProviderUnavailable:
        payload["recommendation"] = "No AI provider is enabled. Facts above are unchanged."
        return payload
    except APIError as exc:
        if getattr(exc, "error_code", "") == "QUOTA_EXCEEDED":
            payload["recommendation"] = str(exc.detail)
            return payload
        raise
    if isinstance(result, dict):
        payload["inference"] = str(result.get("inference") or "")[:4000]
        payload["recommendation"] = str(result.get("recommendation") or "")[:4000]
        payload["origin"] = "ai"
    return payload


GENERIC_ADVISOR_PROMPT = (
    "You are a SIPulse advisor. Return JSON with keys inference and recommendation. "
    "Use only the FACT lines. Never invent revenue, city scores, or lead counts. "
    "If facts are insufficient, say so. Tag nothing as fact unless it appears in the list."
)

BUSINESS_EXPERT_PROMPT = (
    "You are a SIPulse Business Expert and Product Researcher. "
    "Return JSON with keys inference and recommendation. "
    "inference: interpret served markets vs expansion candidates and product mix using only FACT lines. "
    "recommendation: concrete next actions (where to keep serving, where to investigate serving, which products to test or review). "
    "Never invent revenue, conversion rates, city demand grades, or cities that are not in the FACT list. "
    "Served = cities on placed orders. Expansion = only cities listed with evidence (profile gap, customers without orders, product-city absence, or ingested market signals). "
    "If facts are insufficient, say so."
)


def advise_business_expert(*, tenant, user, analysis: dict | None = None) -> dict:
    facts = analysis_facts(analysis or commerce_analysis(tenant))
    payload = {
        "origin": "facts_only",
        "inference": "",
        "recommendation": "",
        "facts": facts,
    }
    if "ai" not in tenant_module_codes(tenant):
        payload["recommendation"] = "Enable the AI module for drafted expert language. Heuristic next actions remain on the analysis."
        payload["origin"] = "heuristic"
        return payload
    try:
        result = AIService.complete(
            tenant=tenant,
            user=user,
            task="business_expert",
            prompt=BUSINESS_EXPERT_PROMPT,
            untrusted="\n".join(f"FACT: {line}" for line in facts),
            schema={"type": "object"},
        )
    except ProviderUnavailable:
        payload["recommendation"] = "No AI provider is enabled. Use the stored served/expansion tables."
        payload["origin"] = "heuristic"
        return payload
    except APIError as exc:
        if getattr(exc, "error_code", "") == "QUOTA_EXCEEDED":
            payload["recommendation"] = str(exc.detail)
            payload["origin"] = "heuristic"
            return payload
        raise
    if isinstance(result, dict):
        payload["inference"] = str(result.get("inference") or "")[:4000]
        payload["recommendation"] = str(result.get("recommendation") or "")[:4000]
        payload["origin"] = "ai"
    return payload
