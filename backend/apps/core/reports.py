from __future__ import annotations

from django.db.models import Sum

from apps.audits.models import Audit
from apps.business.analysis import commerce_analysis
from apps.business.kpis import commerce_kpis
from apps.crm.models import Deal, Pipeline
from apps.leads.models import Lead
from apps.marketing.models import Campaign
from apps.markets.models import MarketSignal
from apps.opportunities.models import Opportunity
from apps.websites.models import Website


def workspace_reports(tenant) -> list[dict]:
    kpis = commerce_kpis(tenant)
    analysis = commerce_analysis(tenant)
    demand = analysis.get("demand") or {}
    products = analysis.get("products") or {}
    audits = Audit.objects.for_tenant(tenant).filter(status=Audit.Status.COMPLETED).count()
    items = [
        {
            "code": "audits",
            "title": "Website intelligence reports",
            "count": audits,
            "available": audits > 0,
            "href": "/app/audits",
            "why": "Printable audit reports from crawled pages.",
        },
        {
            "code": "business",
            "title": "Business analysis",
            "count": kpis.get("orders") or 0,
            "available": bool(kpis.get("available")),
            "href": "/app/business/ecommerce",
            "why": "KPIs and served/expansion tables print only from stored orders or a store sync.",
            "served_cities": len(demand.get("served") or []),
            "expansion_cities": len(demand.get("expansion") or []),
            "top_products": len(products.get("top") or []),
        },
        {
            "code": "markets",
            "title": "Market intelligence",
            "count": MarketSignal.objects.for_tenant(tenant).count(),
            "available": MarketSignal.objects.for_tenant(tenant).exists(),
            "href": "/app/markets",
            "why": "City scores print only after market signals are ingested.",
        },
        {
            "code": "opportunities",
            "title": "Growth opportunities",
            "count": Opportunity.objects.for_tenant(tenant).count(),
            "available": Opportunity.objects.for_tenant(tenant).exists(),
            "href": "/app/opportunities",
            "why": "Recorded evidence, not CRM deals.",
        },
        {
            "code": "marketing",
            "title": "Campaigns",
            "count": Campaign.objects.for_tenant(tenant).count(),
            "available": Campaign.objects.for_tenant(tenant).exists(),
            "href": "/app/marketing",
            "why": "Audience sizes are list or import counts. No invented open rates.",
        },
        {
            "code": "websites",
            "title": "Websites",
            "count": Website.objects.for_tenant(tenant).count(),
            "available": Website.objects.for_tenant(tenant).exists(),
            "href": "/app/websites",
            "why": "Connected properties for this workspace.",
        },
        {
            "code": "leads",
            "title": "Leads",
            "count": Lead.objects.for_tenant(tenant).count(),
            "available": Lead.objects.for_tenant(tenant).exists(),
            "href": "/app/leads",
            "why": "Prospects stored in this workspace. Export is a CSV of stored fields.",
        },
        {
            "code": "crm",
            "title": "CRM funnel",
            "count": Deal.objects.for_tenant(tenant).count(),
            "available": Deal.objects.for_tenant(tenant).exists(),
            "href": "/app/crm",
            "why": "Deal counts and stored amounts by pipeline stage. No forecast is included.",
            "stages": _crm_funnel_stages(tenant),
        },
    ]
    return items


def _crm_funnel_stages(tenant) -> list[dict]:
    pipeline = (
        Pipeline.objects.for_tenant(tenant).filter(is_default=True).prefetch_related("stages").first()
        or Pipeline.objects.for_tenant(tenant).prefetch_related("stages").first()
    )
    if pipeline is None:
        return []
    deals = Deal.objects.for_tenant(tenant).filter(pipeline=pipeline)
    rows = []
    for stage in pipeline.stages.all():
        qs = deals.filter(stage=stage)
        rows.append(
            {
                "name": stage.name,
                "deals": qs.count(),
                "amount": str(qs.aggregate(total=Sum("amount"))["total"] or 0),
            }
        )
    return rows
