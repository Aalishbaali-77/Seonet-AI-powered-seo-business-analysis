from datetime import date, datetime, timedelta

from django.db.models import Avg, Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.auditlog.services import serialize_activity, workspace_activity
from apps.audits.models import Audit
from apps.billing.entitlements import tenant_module_codes
from apps.common.permissions import HasPermissionCode, HasTenant
from apps.core.reports import workspace_reports
from apps.crm.models import Deal
from apps.leads.models import Lead
from apps.marketing.models import Campaign
from apps.opportunities.models import Opportunity
from apps.websites.models import Website


def _numeric_score(scores: dict | None, *keys: str) -> int | None:
    if not scores:
        return None
    values = [float(scores[key]) for key in keys if isinstance(scores.get(key), (int, float))]
    if not values:
        return None
    return int(round(sum(values) / len(values)))


def _score_buckets(queryset, field: str) -> list[dict]:
    scored = queryset.exclude(**{f"{field}__isnull": True})
    rows = []
    for label, low, high in (("0-20", 0, 20), ("21-40", 21, 40), ("41-60", 41, 60), ("61-80", 61, 80), ("81-100", 81, 100)):
        count = scored.filter(**{f"{field}__gte": low, f"{field}__lte": high}).count()
        if count:
            rows.append({"label": label, "count": count})
    return rows


def _ai_usage(tenant) -> dict:
    from apps.ai.credits import usage_snapshot

    snapshot = usage_snapshot(tenant)
    return {
        "credits": snapshot["credits_used"],
        "credits_used": snapshot["credits_used"],
        "credits_limit": snapshot["credits_limit"],
        "credits_remaining": snapshot["credits_remaining"],
        "tokens": snapshot["tokens"],
        "cost": float(snapshot["cost"] or 0),
        "trend": snapshot["by_provider"],
    }


def workspace_lead_intelligence(tenant) -> dict:
    leads = Lead.objects.for_tenant(tenant)
    total = leads.count()
    if not total:
        return {
            "by_industry": [],
            "by_location": [],
            "score_distribution": [],
            "opportunity_distribution": [],
            "data_quality": None,
            "new_leads_over_time": [],
        }
    avg_quality = leads.exclude(quality_score__isnull=True).aggregate(value=Avg("quality_score"))["value"]
    start = timezone.now().date() - timedelta(days=13)
    day_counts: dict[date, int] = {}
    for row in (
        leads.filter(created_at__date__gte=start)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(count=Count("id"))
    ):
        day = row["day"]
        if day is None:
            continue
        day_counts[day.date() if isinstance(day, datetime) else day] = row["count"]
    series = [{"day": (start + timedelta(days=offset)).isoformat(), "count": day_counts.get(start + timedelta(days=offset), 0)} for offset in range(14)]
    return {
        "by_industry": [
            {"industry": row["industry"], "count": row["count"]}
            for row in leads.exclude(industry="").values("industry").annotate(count=Count("id")).order_by("-count")[:8]
        ],
        "by_location": [
            {"location": row["location"], "count": row["count"]}
            for row in leads.exclude(location="").values("location").annotate(count=Count("id")).order_by("-count")[:8]
        ],
        "score_distribution": _score_buckets(leads, "lead_score"),
        "opportunity_distribution": _score_buckets(leads, "opportunity_score"),
        "data_quality": {
            "leads": total,
            "with_website": leads.exclude(website="").count(),
            "with_email": leads.exclude(email="").count(),
            "with_phone": leads.exclude(phone="").count(),
            "with_location": leads.exclude(location="").count(),
            "with_industry": leads.exclude(industry="").count(),
            "avg_quality_score": int(round(avg_quality)) if avg_quality is not None else None,
        },
        "new_leads_over_time": series,
    }


class DashboardOverviewView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant]

    def get(self, request):
        tenant = request.tenant
        websites = Website.objects.for_tenant(tenant)
        audits = Audit.objects.for_tenant(tenant)
        latest = audits.filter(status=Audit.Status.COMPLETED).first()
        leads = Lead.objects.for_tenant(tenant)
        from apps.business.analysis import commerce_analysis
        from apps.business.kpis import commerce_kpis

        modules = tenant_module_codes(tenant)
        kpis = commerce_kpis(tenant) if "business" in modules else {}
        analysis = commerce_analysis(tenant) if "business" in modules else {}
        demand = (analysis or {}).get("demand") or {}
        return Response(
            {
                "overview": {
                    "websites": websites.count(),
                    "audits": audits.filter(status=Audit.Status.COMPLETED).count(),
                    "total_leads": leads.count(),
                    "qualified_leads": leads.filter(status=Lead.Status.QUALIFIED).count(),
                    "opportunities": Deal.objects.for_tenant(tenant).count(),
                    "crm_deals": Deal.objects.for_tenant(tenant).count(),
                    "growth_opportunities": Opportunity.objects.for_tenant(tenant).count(),
                    "campaigns": Campaign.objects.for_tenant(tenant).count(),
                    "crm_synced": leads.filter(crm_synced=True).count(),
                    "commerce_orders": kpis.get("orders") or 0,
                    "commerce_revenue": kpis.get("revenue"),
                    "served_cities": len(demand.get("served") or []),
                    "expansion_cities": len(demand.get("expansion") or []),
                },
                "intelligence": {
                    "website_health": latest.overall_score if latest else None,
                    "seo_score": _numeric_score(latest.scores, "technical_seo", "on_page_seo") if latest else None,
                    "aeo_score": _numeric_score(latest.scores, "aeo") if latest else None,
                    "geo_score": _numeric_score(latest.scores, "geo") if latest else None,
                    "opportunity_score": _numeric_score(latest.scores, "opportunity") if latest else None,
                    "performance_score": _numeric_score(latest.scores, "performance") if latest else None,
                },
                "lead_intelligence": workspace_lead_intelligence(tenant),
                "activity": [serialize_activity(item) for item in workspace_activity(tenant, limit=8)],
                "ai_usage": _ai_usage(tenant),
                "modules": {code: True for code in modules},
            }
        )


class WorkspaceReportsView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "report.view"
    required_module = "reports"

    def get(self, request):
        return Response({"results": workspace_reports(request.tenant)})


class WorkspaceReportsExportView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "report.export"
    required_module = "reports"

    def get(self, request):
        from apps.auditlog.services import write_audit
        from apps.usage.services import record_usage

        rows = workspace_reports(request.tenant)
        write_audit(action="REPORT_EXPORTED", request=request, tenant=request.tenant, resource_type="report", metadata={"count": len(rows)})
        record_usage(tenant=request.tenant, user=request.user, event_type="report_exported", quantity=1)
        fmt = (request.query_params.get("format") or "json").lower()
        if fmt == "csv":
            import csv

            from django.http import HttpResponse

            response = HttpResponse(content_type="text/csv; charset=utf-8")
            response["Content-Disposition"] = 'attachment; filename="sipulse-reports.csv"'
            writer = csv.writer(response)
            writer.writerow(["code", "title", "count", "available", "href", "why"])
            for row in rows:
                writer.writerow([row["code"], row["title"], row["count"], "yes" if row["available"] else "no", row["href"], row["why"]])
            return response
        return Response({"results": rows, "origin": "fact", "why": "Catalog of workspace report sources. Empty modules stay empty."})
