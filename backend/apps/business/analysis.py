from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from apps.business.kpis import commerce_kpis
from apps.business.models import BusinessProfile, CatalogProduct, CommerceCustomer, CommerceOrder, CommerceOrderItem, CommerceReview


def _money(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01")))


def _line_revenue(item: CommerceOrderItem) -> Decimal:
    return (item.unit_price or 0) * (item.quantity or 0) - (item.discount or 0)


def _norm(value: str) -> str:
    return (value or "").strip().lower()


def commerce_analysis(tenant) -> dict:
    kpis = commerce_kpis(tenant)
    profile = BusinessProfile.objects.for_tenant(tenant).first()
    placed = CommerceOrder.objects.for_tenant(tenant).filter(status=CommerceOrder.Status.PLACED)
    items = list(CommerceOrderItem.objects.for_tenant(tenant).filter(order__in=placed).select_related("order", "product"))
    if not kpis.get("available"):
        return {
            "available": False,
            "reason": kpis.get("reason") or "No placed orders to analyze.",
            "business": {},
            "products": {"top": [], "unsold": [], "weak_reviews": []},
            "demand": {"served": [], "thin": [], "expansion": []},
            "next_actions": [],
            "origin": "fact",
        }

    product_stats: dict[str, dict] = {}
    city_stats: dict[str, dict] = {}
    product_city: dict[tuple[str, str], Decimal] = defaultdict(lambda: Decimal("0"))

    for item in items:
        key = (item.product_id and str(item.product_id)) or f"sku:{(item.sku or item.name or item.id)}"
        name = (item.name or (item.product.name if item.product else "") or item.sku or "Unnamed product")[:255]
        sku = item.sku or (item.product.sku if item.product else "")
        stats = product_stats.setdefault(key, {"key": key, "name": name, "sku": sku, "units": Decimal("0"), "revenue": Decimal("0"), "lines": 0})
        qty = item.quantity or Decimal("0")
        stats["units"] += qty
        stats["revenue"] += _line_revenue(item)
        stats["lines"] += 1
        city = (item.order.city or "").strip()
        if city:
            city_row = city_stats.setdefault(city, {"city": city, "orders": set(), "units": Decimal("0"), "revenue": Decimal("0")})
            city_row["orders"].add(item.order_id)
            city_row["units"] += qty
            city_row["revenue"] += _line_revenue(item)
            product_city[(key, city)] += qty

    order_counts = {city: len(row["orders"]) for city, row in city_stats.items()}
    max_orders = max(order_counts.values()) if order_counts else 0
    served = []
    thin = []
    for city, row in sorted(city_stats.items(), key=lambda pair: -len(pair[1]["orders"])):
        orders = len(row["orders"])
        payload = {
            "city": city,
            "orders": orders,
            "units": str(row["units"]),
            "revenue": _money(row["revenue"]),
            "why": f"FACT: {orders} placed orders list city as {city}.",
            "origin": "fact",
        }
        served.append(payload)
        if max_orders >= 4 and orders * 2 < max_orders:
            thin.append(
                {
                    **payload,
                    "why": f"FACT: {city} has {orders} placed orders; the busiest stored city has {max_orders}.",
                }
            )

    top_products = sorted(product_stats.values(), key=lambda row: (-row["revenue"], -row["units"]))[:8]
    sold_ids = {key for key in product_stats if not str(key).startswith("sku:")}
    sold_skus = {(row["sku"] or "").strip().lower() for row in product_stats.values() if row.get("sku")}
    sold_names = {_norm(row["name"]) for row in product_stats.values()}
    unsold = []
    for product in CatalogProduct.objects.for_tenant(tenant).order_by("name")[:200]:
        if str(product.id) in sold_ids:
            continue
        if product.sku and product.sku.strip().lower() in sold_skus:
            continue
        if _norm(product.name) in sold_names:
            continue
        unsold.append(
            {
                "name": product.name,
                "sku": product.sku,
                "why": "FACT: this catalog row has zero placed order lines.",
                "origin": "fact",
            }
        )
        if len(unsold) >= 8:
            break

    weak_reviews = []
    for product in CatalogProduct.objects.for_tenant(tenant):
        negatives = CommerceReview.objects.for_tenant(tenant).filter(product=product, sentiment=CommerceReview.Sentiment.NEGATIVE).count()
        if not negatives:
            continue
        weak_reviews.append(
            {
                "name": product.name,
                "sku": product.sku,
                "negative": negatives,
                "why": f"FACT: {negatives} stored reviews for {product.name} are rated 1–2 stars.",
                "origin": "fact",
            }
        )
    weak_reviews = sorted(weak_reviews, key=lambda row: -row["negative"])[:6]

    expansion = []
    served_names = {_norm(row["city"]) for row in served}
    current_market = (profile.current_market if profile else "") or ""
    if current_market and _norm(current_market) not in served_names:
        expansion.append(
            {
                "city": current_market.strip(),
                "kind": "profile_gap",
                "why": f"FACT: profile current market is {current_market.strip()}, and no placed order lists that city.",
                "origin": "fact",
            }
        )
    customer_cities = list(CommerceCustomer.objects.for_tenant(tenant).exclude(city="").values_list("city", flat=True).distinct())
    for city in customer_cities:
        if _norm(city) in served_names or any(_norm(city) == _norm(row["city"]) for row in expansion):
            continue
        expansion.append(
            {
                "city": city,
                "kind": "customer_without_orders",
                "why": f"FACT: stored customers list city as {city}, and no placed order lists that city.",
                "origin": "fact",
            }
        )
        if len([row for row in expansion if row["kind"] == "customer_without_orders"]) >= 5:
            break

    product_gaps = []
    served_for_gaps = [row for row in served if row["orders"] >= 2][:8]
    for product in top_products[:5]:
        for city_row in served_for_gaps:
            qty = product_city.get((product["key"], city_row["city"])) or Decimal("0")
            if qty > 0:
                continue
            product_gaps.append(
                {
                    "name": product["name"],
                    "sku": product["sku"],
                    "city": city_row["city"],
                    "why": (
                        f"FACT: {product['name']} has 0 placed order lines in {city_row['city']}, "
                        f"which has {city_row['orders']} other placed orders."
                    ),
                    "origin": "fact",
                }
            )
            if len(product_gaps) >= 8:
                break
        if len(product_gaps) >= 8:
            break

    from apps.markets.models import GeoPlace, MarketSignal
    from apps.markets.scoring import DEFAULT_WEIGHTS, score_from_signals, tenant_weights

    weights = tenant_weights(tenant) or DEFAULT_WEIGHTS
    signal_cities = 0
    for place in GeoPlace.objects.filter(kind=GeoPlace.Kind.CITY, country_code="PK"):
        payload = score_from_signals(MarketSignal.objects.for_tenant(tenant).filter(place=place), weights)
        if payload.get("score") is None:
            continue
        signal_cities += 1
        if _norm(place.name) in served_names:
            continue
        expansion.append(
            {
                "city": place.name,
                "kind": "signal_without_orders",
                "score": payload["score"],
                "why": f"FACT: {place.name} has an ingested market score {payload['score']}/100 and 0 placed orders in this workspace.",
                "origin": "fact",
            }
        )
        if len([row for row in expansion if row["kind"] == "signal_without_orders"]) >= 6:
            break

    cancelled = CommerceOrder.objects.for_tenant(tenant).exclude(status=CommerceOrder.Status.PLACED).count()
    top_city = served[0] if served else None
    share = None
    if top_city and kpis["orders"]:
        share = f"{round(100 * top_city['orders'] / kpis['orders'])}%"

    next_actions = []
    if top_city:
        next_actions.append(
            {
                "action": f"Deepen service in {top_city['city']} (already {top_city['orders']} stored orders), then find new prospects in Leads for that market.",
                "origin": "recommendation",
            }
        )
    if thin:
        city = thin[0]["city"]
        next_actions.append(
            {
                "action": f"Treat {city} as a thin served book relative to stored orders, not as a demand grade. Confirm capacity before expanding spend there.",
                "origin": "recommendation",
            }
        )
    if expansion:
        row = expansion[0]
        next_actions.append(
            {
                "action": f"Investigate serving {row['city']} using the stored evidence only. Do not assume a conversion rate.",
                "origin": "recommendation",
            }
        )
    if product_gaps:
        gap = product_gaps[0]
        next_actions.append(
            {
                "action": f"Test offering {gap['name']} in {gap['city']}, where other products already have placed orders.",
                "origin": "recommendation",
            }
        )
    if unsold:
        next_actions.append(
            {
                "action": f"Review unsold catalog rows such as {unsold[0]['name']} (zero placed order lines).",
                "origin": "recommendation",
            }
        )
    if weak_reviews:
        next_actions.append(
            {
                "action": f"Inspect {weak_reviews[0]['name']} quality: {weak_reviews[0]['negative']} stored 1–2 star reviews.",
                "origin": "recommendation",
            }
        )

    return {
        "available": True,
        "reason": "",
        "business": {
            "orders": kpis["orders"],
            "revenue": kpis.get("revenue"),
            "average_order_value": kpis.get("average_order_value"),
            "products": kpis["products"],
            "customers": kpis["customers"],
            "cancelled_or_returned": cancelled,
            "top_city": top_city["city"] if top_city else "",
            "top_city_share": share,
            "channels": kpis.get("by_channel") or [],
            "reviews": kpis.get("reviews") or {},
            "industry": (profile.industry if profile else "") or "",
            "current_market": current_market,
            "goal": (profile.goal if profile else "") or "",
        },
        "products": {
            "top": [
                {
                    "name": row["name"],
                    "sku": row["sku"],
                    "units": str(row["units"]),
                    "revenue": _money(row["revenue"]),
                    "why": f"FACT: {row['name']} has {row['lines']} placed order lines.",
                    "origin": "fact",
                }
                for row in top_products
            ],
            "unsold": unsold,
            "weak_reviews": weak_reviews,
            "gaps": product_gaps,
        },
        "demand": {
            "served": served,
            "thin": thin,
            "expansion": expansion[:12],
            "signal_cities": signal_cities,
        },
        "next_actions": next_actions,
        "origin": "fact",
    }


def analysis_facts(analysis: dict) -> list[str]:
    facts: list[str] = []
    business = analysis.get("business") or {}
    if not analysis.get("available"):
        facts.append(analysis.get("reason") or "No placed orders to analyze.")
        return facts
    facts.append(f"{business.get('orders')} placed orders; stored line revenue {business.get('revenue')}.")
    if business.get("top_city"):
        facts.append(
            f"{business['top_city']} is the busiest stored city ({business.get('top_city_share') or 'n/a'} of placed orders)."
        )
    if business.get("industry"):
        facts.append(f"Profile industry is {business['industry']}.")
    if business.get("current_market"):
        facts.append(f"Profile current market is {business['current_market']}.")
    for row in (analysis.get("demand") or {}).get("served") or []:
        facts.append(row["why"])
    for row in (analysis.get("demand") or {}).get("thin") or []:
        facts.append(row["why"])
    for row in (analysis.get("demand") or {}).get("expansion") or []:
        facts.append(row["why"])
    for row in (analysis.get("products") or {}).get("top") or []:
        facts.append(f"{row['name']} stored line revenue {row['revenue']} across {row['units']} units.")
    for row in (analysis.get("products") or {}).get("unsold") or []:
        facts.append(row["why"])
    for row in (analysis.get("products") or {}).get("gaps") or []:
        facts.append(row["why"])
    for row in (analysis.get("products") or {}).get("weak_reviews") or []:
        facts.append(row["why"])
    reviews = business.get("reviews") or {}
    if reviews.get("count"):
        facts.append(
            f"{reviews['count']} stored reviews; {reviews.get('positive', 0)} positive, {reviews.get('negative', 0)} negative."
        )
    facts.append("Pakistan geography names are reference data, not demand grades. Expansion cities require stored evidence.")
    return facts[:40]


def complete_analysis(*, tenant, user=None, run_ai: bool = False) -> dict:
    from django.utils import timezone

    from apps.billing.entitlements import tenant_module_codes
    from apps.opportunities.services import generate_from_analysis

    analysis = commerce_analysis(tenant)
    created = []
    modules = tenant_module_codes(tenant)
    if analysis.get("available") and "opportunities" in modules:
        created = generate_from_analysis(tenant, analysis)
    expert = {
        "origin": "heuristic",
        "inference": "",
        "recommendation": " ".join(item["action"] for item in (analysis.get("next_actions") or [])[:4]),
        "ran_at": timezone.now().isoformat(),
        "facts": analysis_facts(analysis),
    }
    if run_ai and "ai" in modules and analysis.get("available") and user is not None:
        from apps.ai.advisors import advise_business_expert

        try:
            expert = advise_business_expert(tenant=tenant, user=user, analysis=analysis)
            expert["ran_at"] = timezone.now().isoformat()
            expert.setdefault("facts", analysis_facts(analysis))
        except Exception:  # noqa: BLE001
            expert["recommendation"] = expert.get("recommendation") or "AI expert was not available. Heuristic next actions above still apply."
    profile = BusinessProfile.objects.for_tenant(tenant).first()
    if profile is None:
        profile = BusinessProfile.objects.create(tenant=tenant)
    profile.last_expert = expert
    profile.save(update_fields=["last_expert", "updated_at"])
    if user is not None and analysis.get("available"):
        from apps.notifications.services import notify

        served = len((analysis.get("demand") or {}).get("served") or [])
        notify(
            tenant=tenant,
            user=user,
            title="Business analysis updated",
            body=f"{served} served cities from stored orders. {len(created)} opportunities recorded from evidence.",
            kind="success",
            link="/app/business/ecommerce",
        )
    return {
        "analysis": analysis,
        "expert": expert,
        "opportunities_created": len(created),
        "opportunity_titles": [item.title for item in created],
    }


def start_business_analysis(*, tenant, user):
    from apps.jobs import services as job_services

    job = job_services.create_job(tenant=tenant, user=user, job_type="analyze_business", payload={})
    job.celery_task_id = _enqueue_analysis(str(job.id))
    job.save(update_fields=["celery_task_id", "updated_at"])
    job.refresh_from_db()
    return job


def _enqueue_analysis(job_id: str) -> str:
    from threading import Thread

    from django.conf import settings
    from django.db import connections, transaction

    from workers.tasks import analyze_business

    eager = getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False)
    propagate = getattr(settings, "CELERY_TASK_EAGER_PROPAGATES", False)
    if eager and not propagate:
        def runner() -> None:
            connections.close_all()
            analyze_business(job_id)

        transaction.on_commit(lambda: Thread(target=runner, daemon=True).start())
        return "thread"
    async_result = analyze_business.delay(job_id)
    return str(async_result.id)


def execute_business_analysis(job) -> dict:
    from apps.billing.entitlements import tenant_module_codes
    from apps.jobs import services as job_services

    job_services.mark_running(job, progress=12, result={"stage": "Counting stored orders"})
    job_services.mark_progress(job, progress=45, result={"stage": "Product research"})
    job_services.mark_progress(job, progress=70, result={"stage": "Recording opportunities"})
    summary = complete_analysis(
        tenant=job.tenant,
        user=job.user,
        run_ai="ai" in tenant_module_codes(job.tenant),
    )
    if not (summary.get("analysis") or {}).get("available"):
        job_services.mark_failed(
            job,
            error=(summary.get("analysis") or {}).get("reason") or "No placed orders to analyze.",
            result={"stage": "Analysis failed", "opportunities_created": 0},
        )
        return summary
    job_services.mark_completed(
        job,
        result={
            "stage": "Completed",
            "opportunities_created": summary.get("opportunities_created") or 0,
            "opportunity_titles": summary.get("opportunity_titles") or [],
            "analysis_available": True,
            "expert_origin": (summary.get("expert") or {}).get("origin") or "",
        },
    )
    return summary
