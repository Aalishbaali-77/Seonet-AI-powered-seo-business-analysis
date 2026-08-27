from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import HasPermissionCode, HasTenant
from apps.opportunities.models import Opportunity
from apps.opportunities.serializers import OpportunitySerializer
from apps.opportunities.services import generate_from_evidence


class OpportunityModule:
    required_module = "opportunities"


class OpportunityListCreateView(OpportunityModule, generics.ListCreateAPIView):
    serializer_class = OpportunitySerializer
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    filterset_fields = ("type", "status")
    search_fields = ("title", "evidence")
    ordering_fields = ("created_at", "score", "title")
    ordering = ("-created_at",)

    @property
    def required_permission(self):
        return "opportunity.manage" if self.request.method == "POST" else "opportunity.view"

    def get_queryset(self):
        return Opportunity.objects.for_tenant(self.request.tenant).select_related("geo_place").prefetch_related("related_leads")


class OpportunityDetailView(OpportunityModule, generics.RetrieveUpdateAPIView):
    serializer_class = OpportunitySerializer
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    lookup_field = "id"

    @property
    def required_permission(self):
        return "opportunity.manage" if self.request.method in {"PUT", "PATCH"} else "opportunity.view"

    def get_queryset(self):
        return Opportunity.objects.for_tenant(self.request.tenant).select_related("geo_place").prefetch_related("related_leads")


class OpportunityGenerateView(OpportunityModule, APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "opportunity.manage"

    def post(self, request):
        created = generate_from_evidence(request.tenant)
        if created:
            from apps.auditlog.services import write_audit
            from apps.notifications.services import notify

            notify(
                tenant=request.tenant,
                user=request.user,
                title=f"{len(created)} opportunities recorded from evidence",
                body="Rows were created only from imported orders or ingested market signals.",
                kind="success",
                link="/app/opportunities",
            )
            write_audit(
                action="OPPORTUNITY_GENERATED",
                request=request,
                tenant=request.tenant,
                resource_type="opportunity",
                metadata={"created": len(created)},
            )
        return Response(
            {
                "created": len(created),
                "results": OpportunitySerializer(created, many=True, context={"request": request}).data,
                "note": "Rows are created only from imported orders or ingested market signals.",
            }
        )
