from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audits.models import Audit
from apps.audits.services import start_audit
from apps.auditlog.services import write_audit
from apps.common.exceptions import APIError
from apps.common.permissions import HasPermissionCode, HasTenant
from apps.jobs.serializers import JobSerializer
from apps.websites.models import Website
from apps.websites.serializers import WebsiteSerializer


class WebsiteListCreateView(generics.ListCreateAPIView):
    serializer_class = WebsiteSerializer
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    search_fields = ("domain", "name", "business_name", "url")
    filterset_fields = ("status",)
    ordering_fields = ("updated_at", "domain", "created_at")

    def get_required_permission(self):
        return "website.create" if self.request.method == "POST" else "website.view"

    @property
    def required_permission(self):
        return self.get_required_permission()

    def get_queryset(self):
        return Website.objects.for_tenant(self.request.tenant).prefetch_related("audits").select_related("code_access")

    def perform_create(self, serializer):
        website = serializer.save()
        write_audit(
            action="WEBSITE_CREATED",
            request=self.request,
            resource_type="website",
            resource_id=website.id,
        )


class WebsiteDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = WebsiteSerializer
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    lookup_field = "id"

    @property
    def required_permission(self):
        if self.request.method == "DELETE":
            return "website.delete"
        if self.request.method in {"PUT", "PATCH"}:
            return "website.create"
        return "website.view"

    def get_queryset(self):
        return Website.objects.for_tenant(self.request.tenant)

    def perform_update(self, serializer):
        website = serializer.save()
        write_audit(
            action="WEBSITE_UPDATED",
            request=self.request,
            resource_type="website",
            resource_id=website.id,
            metadata={"status": website.status},
        )

    def perform_destroy(self, instance):
        write_audit(
            action="WEBSITE_DELETED",
            request=self.request,
            resource_type="website",
            resource_id=instance.id,
            metadata={"domain": instance.domain},
        )
        instance.delete()


class WebsiteAuditStartView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "website.audit"

    def post(self, request, id):
        website = Website.objects.for_tenant(request.tenant).filter(id=id).first()
        if website is None:
            return Response(
                {
                    "error": {
                        "code": "NOT_FOUND",
                        "message": "Resource not found.",
                        "details": {},
                        "request_id": getattr(request, "request_id", ""),
                    }
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        job = start_audit(website=website, user=request.user)
        return Response(JobSerializer(job).data, status=status.HTTP_202_ACCEPTED)


class WebsitePerformanceTrendsView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "website.view"

    def get(self, request, id):
        website = Website.objects.for_tenant(request.tenant).filter(id=id).first()
        if website is None:
            return Response({"error": {"code": "NOT_FOUND", "message": "Resource not found.", "details": {}, "request_id": getattr(request, "request_id", "")}}, status=status.HTTP_404_NOT_FOUND)
        audits = (
            Audit.objects.for_tenant(request.tenant)
            .filter(website=website, status=Audit.Status.COMPLETED)
            .order_by("completed_at", "created_at")
        )
        points = []
        for audit in audits:
            snapshot = (audit.summary or {}).get("performance") or {}
            kpis = snapshot.get("kpis") or {}
            points.append(
                {
                    "audit_id": str(audit.id),
                    "completed_at": audit.completed_at or audit.created_at,
                    "overall": snapshot.get("overall_score") or audit.scores.get("performance"),
                    "technical": snapshot.get("technical_score") or audit.scores.get("technical_performance"),
                    "ux": snapshot.get("ux_score"),
                    "median_ttfb_ms": kpis.get("median_ttfb_ms") or (audit.summary or {}).get("avg_ttfb_ms"),
                    "p75_ttfb_ms": kpis.get("p75_ttfb_ms"),
                    "p95_ttfb_ms": kpis.get("p95_ttfb_ms"),
                    "median_html_bytes": kpis.get("median_html_bytes"),
                }
            )
        latest = points[-1] if points else None
        return Response({"website_id": str(website.id), "domain": website.domain, "points": points, "latest": latest})


def _website_or_404(request, id):
    website = Website.objects.for_tenant(request.tenant).filter(id=id).first()
    if website is None:
        return None, Response(
            {"error": {"code": "NOT_FOUND", "message": "Resource not found.", "details": {}, "request_id": getattr(request, "request_id", "")}},
            status=status.HTTP_404_NOT_FOUND,
        )
    return website, None


class WebsiteAccessView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    @property
    def required_permission(self):
        return "website.audit" if self.request.method in {"PUT", "POST", "DELETE"} else "website.view"

    def get(self, request, id):
        from apps.websites.models import WebsiteAccess
        from apps.websites.serializers import access_public

        website, error = _website_or_404(request, id)
        if error:
            return error
        access = WebsiteAccess.objects.for_tenant(request.tenant).filter(website=website).first()
        if access is None:
            return Response({"connected": False, "access": None})
        return Response({"connected": access.status == WebsiteAccess.Status.CONNECTED, "access": access_public(access)})

    def put(self, request, id):
        from django.utils import timezone

        from apps.common.crypto import decrypt_json, encrypt_json
        from apps.websites.models import WebsiteAccess
        from apps.websites.serializers import access_public
        from apps.websites.transports import build_transport

        website, error = _website_or_404(request, id)
        if error:
            return error
        body = request.data or {}
        kind = str(body.get("kind") or "").strip()
        allowed = {choice[0] for choice in WebsiteAccess.Kind.choices}
        if kind not in allowed:
            raise APIError("Choose WordPress, FTP, SFTP, or cPanel.", code="VALIDATION_ERROR")
        config = {
            "host": str(body.get("host") or "").strip(),
            "port": body.get("port") or "",
            "root_path": str(body.get("root_path") or "").strip(),
            "wp_url": str(body.get("wp_url") or website.url).strip(),
            "username": str(body.get("username") or "").strip(),
        }
        access = WebsiteAccess.objects.for_tenant(request.tenant).filter(website=website).first()
        existing = decrypt_json(access.secret_blob) if access else {}
        password = str(body.get("password") or "")
        secrets = {"username": config["username"], "password": password or existing.get("password") or ""}
        transport = build_transport(kind=kind, config=config, secrets=secrets, website_url=website.url)
        message = transport.test()
        if access is None:
            access = WebsiteAccess(tenant=request.tenant, website=website)
        access.kind = kind
        access.config = config
        access.secret_blob = encrypt_json(secrets)
        access.status = WebsiteAccess.Status.CONNECTED
        access.last_tested_at = timezone.now()
        access.last_error = ""
        access.save()
        write_audit(action="WEBSITE_ACCESS_CONNECTED", request=request, resource_type="website", resource_id=website.id, metadata={"kind": kind})
        return Response({"connected": True, "access": access_public(access), "message": message})

    def delete(self, request, id):
        from apps.websites.models import WebsiteAccess

        website, error = _website_or_404(request, id)
        if error:
            return error
        WebsiteAccess.objects.for_tenant(request.tenant).filter(website=website).delete()
        write_audit(action="WEBSITE_ACCESS_REMOVED", request=request, resource_type="website", resource_id=website.id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class WebsiteFixPlanView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "website.view"

    def get(self, request, id):
        from apps.websites.fixes import plan_fixes
        from apps.websites.models import WebsiteAccess

        website, error = _website_or_404(request, id)
        if error:
            return error
        audit_id = request.query_params.get("audit") or (website.audits.filter(status=Audit.Status.COMPLETED).values_list("id", flat=True).first())
        audit = Audit.objects.for_tenant(request.tenant).filter(id=audit_id, website=website, status=Audit.Status.COMPLETED).first() if audit_id else None
        if audit is None:
            raise APIError("Complete an audit before planning recommended fixes.", code="VALIDATION_ERROR")
        access = WebsiteAccess.objects.for_tenant(request.tenant).filter(website=website).first()
        wordpress = bool(access and access.kind == WebsiteAccess.Kind.WORDPRESS)
        can_write = bool(access and access.kind != WebsiteAccess.Kind.WORDPRESS and access.status == WebsiteAccess.Status.CONNECTED)
        return Response({"audit_id": str(audit.id), "access_connected": bool(access and access.status == WebsiteAccess.Status.CONNECTED), **plan_fixes(website=website, audit=audit, can_write_files=can_write, wordpress=wordpress)})


class WebsiteApplyFixesView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "website.audit"

    def post(self, request, id):
        from apps.websites.fix_jobs import start_fix_run

        website, error = _website_or_404(request, id)
        if error:
            return error
        audit_id = (request.data or {}).get("audit_id") or request.query_params.get("audit")
        audit = Audit.objects.for_tenant(request.tenant).filter(id=audit_id, website=website).first() if audit_id else website.audits.filter(status=Audit.Status.COMPLETED).first()
        if audit is None:
            raise APIError("Select the completed audit to keep as the pre-fix baseline.", code="VALIDATION_ERROR")
        job = start_fix_run(website=website, user=request.user, audit=audit)
        return Response(JobSerializer(job).data, status=status.HTTP_202_ACCEPTED)


class WebsiteFixRunListView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "website.view"

    def get(self, request, id):
        from apps.websites.models import AuditFixRun
        from apps.websites.serializers import fix_run_public

        website, error = _website_or_404(request, id)
        if error:
            return error
        rows = AuditFixRun.objects.for_tenant(request.tenant).filter(website=website).select_related("baseline_audit", "followup_audit")[:20]
        return Response({"results": [fix_run_public(item) for item in rows]})


class WebsiteFixRunDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "website.view"

    def get(self, request, id, run_id):
        from apps.websites.models import AuditFixRun
        from apps.websites.serializers import fix_run_public

        website, error = _website_or_404(request, id)
        if error:
            return error
        run = AuditFixRun.objects.for_tenant(request.tenant).filter(website=website, id=run_id).first()
        if run is None:
            return Response({"error": {"code": "NOT_FOUND", "message": "Resource not found.", "details": {}, "request_id": getattr(request, "request_id", "")}}, status=status.HTTP_404_NOT_FOUND)
        return Response(fix_run_public(run))


class WebsiteKeywordRankView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]

    @property
    def required_permission(self):
        return "website.audit" if self.request.method == "POST" else "website.view"

    def get(self, request, id):
        from apps.websites.keywords import run_public
        from apps.websites.models import KeywordRankRun

        website, error = _website_or_404(request, id)
        if error:
            return error
        run = KeywordRankRun.objects.for_tenant(request.tenant).filter(website=website).order_by("-created_at").first()
        if run is None:
            return Response({"run": None})
        return Response({"run": run_public(run)})

    def post(self, request, id):
        from apps.websites.keywords import start_keyword_rank

        website, error = _website_or_404(request, id)
        if error:
            return error
        job = start_keyword_rank(website=website, user=request.user)
        return Response(JobSerializer(job).data, status=status.HTTP_202_ACCEPTED)
