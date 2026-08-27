from collections import defaultdict

from django.http import HttpResponse
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audits.models import Audit, AuditIssue, AuditRecommendation, CrawlPage
from apps.audits.performance import compare_snapshots, page_api_payload, page_detail_payload
from apps.audits.serializers import AuditDetailSerializer, AuditIssueSerializer, AuditRecommendationSerializer, AuditSerializer
from apps.common.exceptions import APIError
from apps.common.permissions import HasPermissionCode, HasTenant
from apps.common.pagination import StandardPagination


class AuditListView(generics.ListAPIView):
    serializer_class = AuditSerializer
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "website.view"
    filterset_fields = ("status", "website")

    def get_queryset(self):
        return Audit.objects.for_tenant(self.request.tenant).select_related("website")


class AuditDetailView(generics.RetrieveAPIView):
    serializer_class = AuditDetailSerializer
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "website.view"
    lookup_field = "id"

    def get_queryset(self):
        return Audit.objects.for_tenant(self.request.tenant).prefetch_related("issues", "recommendations").select_related("website")


class AuditIssueListView(generics.ListAPIView):
    serializer_class = AuditIssueSerializer
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "website.view"
    filterset_fields = ("severity", "category", "status")
    search_fields = ("title",)

    def get_queryset(self):
        return AuditIssue.objects.for_tenant(self.request.tenant).filter(audit_id=self.kwargs["id"])


class AuditIssueDetailView(generics.UpdateAPIView):
    serializer_class = AuditIssueSerializer
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "website.audit"
    lookup_field = "id"
    lookup_url_kwarg = "issue_id"
    http_method_names = ["patch"]

    def get_queryset(self):
        return AuditIssue.objects.for_tenant(self.request.tenant).filter(audit_id=self.kwargs["id"])


class AuditRecommendationListView(generics.ListAPIView):
    serializer_class = AuditRecommendationSerializer
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "website.view"

    def get_queryset(self):
        return (
            AuditRecommendation.objects.for_tenant(self.request.tenant)
            .filter(audit_id=self.kwargs["id"])
            .select_related("issue")
        )


class AuditReportView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "website.view"

    def get(self, request, id):
        audit = (
            Audit.objects.for_tenant(request.tenant)
            .select_related("website", "crawl")
            .prefetch_related("issues", "recommendations")
            .filter(id=id)
            .first()
        )
        if audit is None:
            raise APIError("Resource not found.", code="NOT_FOUND", status_code=404)
        grouped: dict[str, list] = defaultdict(list)
        for issue in audit.issues.all():
            grouped[issue.category].append(AuditIssueSerializer(issue).data)
        return Response(
            {
                "audit": AuditDetailSerializer(audit).data,
                "website": {
                    "id": str(audit.website_id),
                    "name": audit.website.name,
                    "domain": audit.website.domain,
                    "url": audit.website.url,
                    "industry": audit.website.industry,
                    "keywords": audit.website.keywords,
                    "target_markets": audit.website.target_markets,
                    "competitors": audit.website.competitors,
                },
                "issues_by_category": grouped,
                "recommendations": AuditRecommendationSerializer(audit.recommendations.all(), many=True).data,
                "export": "json",
            }
        )


def _tenant_audit(request, id) -> Audit:
    audit = (
        Audit.objects.for_tenant(request.tenant)
        .select_related("website", "crawl")
        .filter(id=id)
        .first()
    )
    if audit is None:
        raise APIError("Resource not found.", code="NOT_FOUND", status_code=404)
    return audit


class AuditPerformanceView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "website.view"

    def get(self, request, id):
        audit = _tenant_audit(request, id)
        snapshot = (audit.summary or {}).get("performance") or {}
        issues = AuditIssue.objects.for_tenant(request.tenant).filter(audit=audit, category="performance")
        counts = {
            "critical": issues.filter(severity="critical").count(),
            "high": issues.filter(severity="high").count(),
            "medium": issues.filter(severity="medium").count(),
            "low": issues.filter(severity="low").count(),
            "info": issues.filter(severity="info").count(),
        }
        return Response(
            {
                "audit_id": str(audit.id),
                "website_id": str(audit.website_id),
                "website_domain": audit.website.domain,
                "completed_at": audit.completed_at,
                "scores": {
                    "overall": snapshot.get("overall_score") or audit.scores.get("performance"),
                    "technical": snapshot.get("technical_score") or audit.scores.get("technical_performance") or audit.scores.get("performance"),
                    "ux": snapshot.get("ux_score") or audit.scores.get("ux_cwv"),
                },
                "snapshot": snapshot,
                "issue_counts": counts,
                "recommendations": [
                    {
                        "title": rec.title,
                        "recommendation": rec.recommendation,
                        "code": rec.issue.code if rec.issue_id else "",
                        "severity": rec.issue.severity if rec.issue_id else "",
                        "evidence": rec.verified_finding,
                        "ai_interpretation": rec.ai_interpretation,
                    }
                    for rec in AuditRecommendation.objects.filter(audit=audit, issue__category="performance")
                    .select_related("issue")
                    .order_by("-issue__priority")[:8]
                ],
            }
        )


class AuditPageListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "website.view"
    pagination_class = StandardPagination
    search_fields = ("url", "title")
    ordering_fields = ("ttfb_ms", "html_size_bytes", "page_score", "url", "status_code")
    ordering = ("-ttfb_ms", "url")

    def get_queryset(self):
        audit = _tenant_audit(self.request, self.kwargs["id"])
        if audit.crawl_id is None:
            return CrawlPage.objects.none()
        qs = CrawlPage.objects.for_tenant(self.request.tenant).filter(crawl_id=audit.crawl_id)
        search = (self.request.query_params.get("search") or "").strip()
        if search:
            qs = qs.filter(url__icontains=search)
        compression = (self.request.query_params.get("compression") or "").strip()
        if compression:
            qs = qs.filter(compression=compression)
        return qs.order_by("-ttfb_ms", "url")

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        rows = [page_api_payload(item) for item in (page or queryset)]
        if page is not None:
            return self.get_paginated_response(rows)
        return Response({"results": rows})


class AuditPageDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "website.view"

    def get(self, request, id, page_id):
        audit = _tenant_audit(request, id)
        page = CrawlPage.objects.for_tenant(request.tenant).filter(id=page_id, crawl_id=audit.crawl_id).first()
        if page is None:
            raise APIError("Resource not found.", code="NOT_FOUND", status_code=404)
        issues_qs = (
            AuditIssue.objects.for_tenant(request.tenant)
            .filter(audit=audit, category="performance")
            .order_by("-priority")
        )
        issues = [item for item in issues_qs if page.url in (item.affected_urls or [])]
        payload = page_detail_payload(page)
        payload["issues"] = AuditIssueSerializer(issues, many=True).data
        payload["recommendations"] = [
            {"title": item.title, "recommendation": item.recommendation, "severity": item.severity, "evidence": item.evidence}
            for item in issues
        ]
        return Response(payload)


class AuditPerformanceCompareView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "website.view"

    def get(self, request, id):
        audit = _tenant_audit(request, id)
        other_id = request.query_params.get("other")
        previous = None
        if other_id:
            previous = Audit.objects.for_tenant(request.tenant).filter(id=other_id, website_id=audit.website_id).first()
        if previous is None:
            previous = (
                Audit.objects.for_tenant(request.tenant)
                .filter(website_id=audit.website_id, status=Audit.Status.COMPLETED)
                .exclude(id=audit.id)
                .order_by("-completed_at", "-created_at")
                .first()
            )
        current = (audit.summary or {}).get("performance") or {}
        prior = (previous.summary or {}).get("performance") if previous else None
        return Response(
            {
                "current_audit_id": str(audit.id),
                "previous_audit_id": str(previous.id) if previous else None,
                "comparison": compare_snapshots(current, prior),
                "regression": current.get("regression") or {"detected": False, "changes": []},
            }
        )


class AuditPageExportView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "website.view"

    def get(self, request, id):
        audit = _tenant_audit(request, id)
        if audit.crawl_id is None:
            raise APIError("No crawl is attached to this audit.", code="NOT_FOUND", status_code=404)
        pages = CrawlPage.objects.for_tenant(request.tenant).filter(crawl_id=audit.crawl_id).order_by("-ttfb_ms")
        lines = ["url,status,performance,ttfb_ms,html_size_bytes,transfer_bytes,redirects,compression,protocol"]
        for page in pages.iterator():
            row = page_api_payload(page)
            lines.append(
                ",".join(
                    [
                        f"\"{row['url']}\"",
                        str(row.get("status_code") or ""),
                        str(row.get("page_score") or ""),
                        str(row.get("ttfb_ms") or ""),
                        str(row.get("html_size_bytes") or ""),
                        str(row.get("transfer_bytes") or ""),
                        str(row.get("redirect_count") or ""),
                        str(row.get("compression") or ""),
                        str(row.get("http_protocol") or ""),
                    ]
                )
            )
        content = "\n".join(lines)
        response = HttpResponse(content, content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="performance-{audit.website.domain}.csv"'
        return response
