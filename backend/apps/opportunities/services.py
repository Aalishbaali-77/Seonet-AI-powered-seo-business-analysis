from __future__ import annotations

from apps.markets.catalog import ensure_geo_catalog
from apps.opportunities.models import Opportunity


def _exists(tenant, title: str) -> bool:
    return Opportunity.objects.for_tenant(tenant).filter(title=title).exists()


def generate_from_evidence(tenant) -> list[Opportunity]:
    from apps.business.analysis import commerce_analysis

    return generate_from_analysis(tenant, commerce_analysis(tenant))


def generate_from_analysis(tenant, analysis: dict) -> list[Opportunity]:
    created: list[Opportunity] = []
    if not analysis.get("available"):
        ensure_geo_catalog()
        return _from_market_signals(tenant, created)
    demand = analysis.get("demand") or {}
    for row in (demand.get("served") or [])[:8]:
        city = row["city"]
        title = f"Deepen coverage in {city}"
        if _exists(tenant, title):
            continue
        created.append(
            Opportunity.objects.create(
                tenant=tenant,
                title=title,
                type=Opportunity.Type.GEOGRAPHIC,
                evidence=row["why"],
                recommended_action=f"Confirm capacity for {city}, then run lead discovery for that market in the existing Leads module.",
                potential_impact="Based on existing order geography only; revenue is not projected.",
                origin="system",
                score=None,
            )
        )
    for row in (demand.get("thin") or [])[:5]:
        city = row["city"]
        title = f"Grow the thin book in {city}"
        if _exists(tenant, title):
            continue
        created.append(
            Opportunity.objects.create(
                tenant=tenant,
                title=title,
                type=Opportunity.Type.GEOGRAPHIC,
                evidence=row["why"],
                recommended_action=f"Treat {city} as smaller than the busiest stored city. Do not assign a demand grade.",
                potential_impact="Relative to stored order counts only.",
                origin="system",
            )
        )
    for row in (demand.get("expansion") or [])[:8]:
        city = row["city"]
        title = f"Investigate serving {city}"
        if _exists(tenant, title):
            continue
        created.append(
            Opportunity.objects.create(
                tenant=tenant,
                title=title,
                type=Opportunity.Type.GEOGRAPHIC,
                evidence=row["why"],
                recommended_action=f"Do not invent demand for {city}. Validate with leads only after this evidence is reviewed.",
                potential_impact="Unserved relative to stored orders or ingested signals; no revenue forecast.",
                origin="system",
                score=row.get("score"),
            )
        )
    products = analysis.get("products") or {}
    for row in (products.get("gaps") or [])[:6]:
        title = f"Offer {row['name']} in {row['city']}"
        if _exists(tenant, title):
            continue
        created.append(
            Opportunity.objects.create(
                tenant=tenant,
                title=title,
                type=Opportunity.Type.CROSS_SELL,
                evidence=row["why"],
                recommended_action=f"Test listing {row['name']} where {row['city']} already has other placed orders.",
                potential_impact="Product-city absence on stored orders. Conversion is not estimated.",
                origin="system",
            )
        )
    for row in (products.get("unsold") or [])[:4]:
        title = f"Review unsold catalog item {row['name']}"
        if _exists(tenant, title):
            continue
        created.append(
            Opportunity.objects.create(
                tenant=tenant,
                title=title,
                type=Opportunity.Type.PRODUCT,
                evidence=row["why"],
                recommended_action="Decide whether to promote, bundle, or delist. Zero order lines is not a forecast.",
                potential_impact="Catalog presence only.",
                origin="system",
            )
        )
    for row in (products.get("weak_reviews") or [])[:3]:
        title = f"Improve {row['name']} after negative reviews"
        if _exists(tenant, title):
            continue
        created.append(
            Opportunity.objects.create(
                tenant=tenant,
                title=title,
                type=Opportunity.Type.PRODUCT,
                evidence=row["why"],
                recommended_action="Read the stored reviews, then fix product or listing issues. Sentiment is from star ratings.",
                potential_impact="Review counts only; NPS is not invented.",
                origin="system",
            )
        )
    return _from_market_signals(tenant, created)


def _from_market_signals(tenant, created: list[Opportunity]) -> list[Opportunity]:
    from apps.markets.catalog import ensure_geo_catalog
    from apps.markets.models import GeoPlace, MarketSignal
    from apps.markets.scoring import DEFAULT_WEIGHTS, score_from_signals, tenant_weights

    ensure_geo_catalog()
    weights = tenant_weights(tenant)
    for city in GeoPlace.objects.filter(kind=GeoPlace.Kind.CITY, country_code="PK"):
        payload = score_from_signals(MarketSignal.objects.for_tenant(tenant).filter(place=city), weights or DEFAULT_WEIGHTS)
        if payload.get("score") is None:
            continue
        title = f"Market opening in {city.name}"
        if _exists(tenant, title):
            continue
        created.append(
            Opportunity.objects.create(
                tenant=tenant,
                title=title,
                type=Opportunity.Type.MARKET,
                score=payload["score"],
                evidence=payload["why"],
                recommended_action=f"Review {city.name} signals, then find leads in that market from the existing Leads module.",
                potential_impact="Score uses ingested MarketSignal rows only.",
                origin="system",
                geo_place=city,
                confidence=payload.get("coverage"),
            )
        )
    return created
