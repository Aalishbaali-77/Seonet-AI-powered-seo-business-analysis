import csv

from django.db.models import Count, Q
from django.http import HttpResponse
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.exceptions import APIError
from apps.common.permissions import HasPermissionCode, HasTenant
from apps.jobs.serializers import JobSerializer
from apps.leads.models import ICP, Lead, LeadList, LeadSearch
from apps.leads.scoring import apply_lead_score, score_lead
from apps.leads.serializers import ICPSerializer, LeadListSerializer, LeadSearchSerializer, LeadSerializer
from apps.leads.services import confirm_icp, start_discovery


class LeadModule:
    required_module = "leads"


def filtered_leads(request):
    qs = Lead.objects.for_tenant(request.tenant)
    status_value = request.query_params.get("status")
    if status_value:
        qs = qs.filter(status=status_value)
    source = request.query_params.get("source")
    if source:
        qs = qs.filter(source=source)
    search = (request.query_params.get("search") or "").strip()
    if search:
        qs = qs.filter(
            Q(company_name__icontains=search)
            | Q(industry__icontains=search)
            | Q(location__icontains=search)
            | Q(email__icontains=search)
        )
    return qs


class ICPListCreateView(LeadModule, generics.ListCreateAPIView):
    serializer_class = ICPSerializer
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]

    @property
    def required_permission(self):
        return "lead.create" if self.request.method == "POST" else "lead.view"

    def get_queryset(self):
        return ICP.objects.for_tenant(self.request.tenant)


class ICPConfirmView(LeadModule, APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "lead.create"

    def post(self, request, id):
        icp = ICP.objects.for_tenant(request.tenant).filter(id=id).first()
        if icp is None:
            raise APIError("Resource not found.", code="NOT_FOUND", status_code=404)
        confirm_icp(icp)
        return Response(ICPSerializer(icp).data)


class LeadSearchStartView(LeadModule, APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "lead.create"

    def post(self, request):
        icp_id = request.data.get("icp")
        icp = ICP.objects.for_tenant(request.tenant).filter(id=icp_id).first()
        if icp is None:
            raise APIError("Confirm an ICP first.", code="VALIDATION_ERROR", status_code=400)
        geo_place = None
        place_id = request.data.get("geo_place")
        if place_id:
            from apps.markets.models import GeoPlace

            geo_place = GeoPlace.objects.filter(id=place_id).first()
            if geo_place is None:
                raise APIError("Market place not found.", code="NOT_FOUND", status_code=404)
        search = start_discovery(icp=icp, user=request.user, geo_place=geo_place)
        return Response(
            {"search": LeadSearchSerializer(search).data, "job": JobSerializer(search.job).data},
            status=status.HTTP_202_ACCEPTED,
        )


class LeadSearchListView(LeadModule, generics.ListAPIView):
    serializer_class = LeadSearchSerializer
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "lead.view"

    def get_queryset(self):
        return LeadSearch.objects.for_tenant(self.request.tenant)


class LeadListCreateView(LeadModule, generics.ListCreateAPIView):
    serializer_class = LeadSerializer
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    search_fields = ("company_name", "industry", "location", "email")
    filterset_fields = ("status", "source", "crm_synced")
    ordering_fields = ("updated_at", "lead_score", "company_name")

    @property
    def required_permission(self):
        return "lead.create" if self.request.method == "POST" else "lead.view"

    def get_queryset(self):
        return Lead.objects.for_tenant(self.request.tenant)

    def perform_create(self, serializer):
        lead = serializer.save()
        from apps.integrations.push import push_lead

        push_lead(self.request.tenant, lead, event="lead.created")


class LeadDetailView(LeadModule, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = LeadSerializer
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    lookup_field = "id"

    @property
    def required_permission(self):
        if self.request.method == "DELETE":
            return "lead.delete"
        if self.request.method in {"PUT", "PATCH"}:
            return "lead.create"
        return "lead.view"

    def get_queryset(self):
        return Lead.objects.for_tenant(self.request.tenant)

    def perform_update(self, serializer):
        lead = serializer.save()
        from apps.integrations.push import push_lead

        push_lead(self.request.tenant, lead, event="lead.updated")


class LeadListCollectionView(LeadModule, generics.ListCreateAPIView):
    serializer_class = LeadListSerializer
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]

    @property
    def required_permission(self):
        return "lead.create" if self.request.method == "POST" else "lead.view"

    def get_queryset(self):
        return LeadList.objects.for_tenant(self.request.tenant).annotate(lead_count=Count("leads"))


class LeadListDetailView(LeadModule, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = LeadListSerializer
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    lookup_field = "id"

    @property
    def required_permission(self):
        if self.request.method == "DELETE":
            return "lead.delete"
        if self.request.method in {"PUT", "PATCH"}:
            return "lead.create"
        return "lead.view"

    def get_queryset(self):
        return LeadList.objects.for_tenant(self.request.tenant).annotate(lead_count=Count("leads"))

    def retrieve(self, request, *args, **kwargs):
        item = self.get_object()
        data = self.get_serializer(item).data
        data["leads"] = LeadSerializer(Lead.objects.for_tenant(request.tenant).filter(lists=item), many=True).data
        return Response(data)


class LeadListMembersView(LeadModule, APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "lead.create"

    def _list(self, request, id):
        item = LeadList.objects.for_tenant(request.tenant).filter(id=id).first()
        if item is None:
            raise APIError("Resource not found.", code="NOT_FOUND", status_code=404)
        return item

    def post(self, request, id):
        item = self._list(request, id)
        ids = request.data.get("lead_ids") or []
        leads = Lead.objects.for_tenant(request.tenant).filter(id__in=ids)
        item.leads.add(*leads)
        return Response({"id": str(item.id), "added": leads.count()})

    def delete(self, request, id):
        item = self._list(request, id)
        ids = request.data.get("lead_ids") or []
        leads = Lead.objects.for_tenant(request.tenant).filter(id__in=ids)
        item.leads.remove(*leads)
        return Response({"id": str(item.id), "removed": leads.count()})


class LeadScoreView(LeadModule, APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "lead.view"

    def post(self, request):
        icp = ICP.objects.for_tenant(request.tenant).filter(status=ICP.Status.CONFIRMED).order_by("-confirmed_at").first()
        qs = Lead.objects.for_tenant(request.tenant)
        ids = request.data.get("lead_ids") or []
        if ids:
            qs = qs.filter(id__in=ids)
        scored = 0
        for lead in qs:
            apply_lead_score(lead, icp)
            scored += 1
        return Response({"scored": scored, "icp": str(icp.id) if icp else None})


class LeadExportView(LeadModule, APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "lead.export"

    def get(self, request):
        qs = filtered_leads(request).order_by("company_name", "id")
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="sipulse-leads.csv"'
        writer = csv.writer(response)
        writer.writerow(
            [
                "company_name",
                "industry",
                "location",
                "website",
                "phone",
                "email",
                "source",
                "status",
                "lead_score",
                "quality_score",
                "crm_synced",
                "origin",
            ]
        )
        count = 0
        for lead in qs.iterator():
            writer.writerow(
                [
                    lead.company_name,
                    lead.industry,
                    lead.location,
                    lead.website,
                    lead.phone,
                    lead.email,
                    lead.source,
                    lead.status,
                    lead.lead_score if lead.lead_score is not None else "",
                    lead.quality_score if lead.quality_score is not None else "",
                    "yes" if lead.crm_synced else "no",
                    lead.origin,
                ]
            )
            count += 1
        from apps.auditlog.services import write_audit
        from apps.usage.services import record_usage

        record_usage(
            tenant=request.tenant,
            user=request.user,
            event_type="lead_exported",
            quantity=count,
            metadata={"status": request.query_params.get("status") or "", "search": request.query_params.get("search") or ""},
        )
        write_audit(
            action="LEAD_EXPORTED",
            request=request,
            tenant=request.tenant,
            resource_type="lead",
            metadata={"count": count},
        )
        return response


class LeadEnrichView(LeadModule, APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "lead.enrich"

    def post(self, request, id):
        lead = Lead.objects.for_tenant(request.tenant).filter(id=id).first()
        if lead is None:
            raise APIError("Resource not found.", code="NOT_FOUND", status_code=404)
        from apps.leads.enrichment import enrich_lead

        result = enrich_lead(lead, user=request.user)
        lead.refresh_from_db()
        return Response(
            {
                "lead": LeadSerializer(lead).data,
                "filled": result["filled"],
                "missing_fields": result["missing_fields"],
                "sources": result["sources"],
                "errors": result["errors"],
                "why": result["why"],
            }
        )


class LeadBulkEnrichView(LeadModule, APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "lead.enrich"

    def post(self, request):
        from apps.leads.enrichment import start_bulk_enrich

        ids = [str(item) for item in (request.data.get("lead_ids") or []) if str(item).strip()]
        job = start_bulk_enrich(tenant=request.tenant, user=request.user, lead_ids=ids)
        return Response({"job": JobSerializer(job).data}, status=status.HTTP_202_ACCEPTED)
