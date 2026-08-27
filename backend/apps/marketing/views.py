import csv

from django.http import HttpResponse
from django.utils import timezone
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.exceptions import APIError
from apps.common.permissions import HasPermissionCode, HasTenant
from apps.marketing.models import Campaign
from apps.marketing.serializers import CampaignSerializer
from apps.marketing.services import audience_count, audience_rows


class MarketingModule:
    required_module = "marketing"


class CampaignListCreateView(MarketingModule, generics.ListCreateAPIView):
    serializer_class = CampaignSerializer
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    filterset_fields = ("status", "channel", "audience_type")
    search_fields = ("name", "offer_title")
    ordering = ("-created_at",)

    @property
    def required_permission(self):
        return "marketing.manage" if self.request.method == "POST" else "marketing.view"

    def get_queryset(self):
        return Campaign.objects.for_tenant(self.request.tenant).select_related("lead_list", "opportunity")


class CampaignDetailView(MarketingModule, generics.RetrieveUpdateAPIView):
    serializer_class = CampaignSerializer
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    lookup_field = "id"

    @property
    def required_permission(self):
        return "marketing.manage" if self.request.method in {"PUT", "PATCH"} else "marketing.view"

    def get_queryset(self):
        return Campaign.objects.for_tenant(self.request.tenant).select_related("lead_list", "opportunity")


class CampaignPreviewView(MarketingModule, APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "marketing.view"

    def get(self, request):
        payload = audience_count(
            request.tenant,
            audience_type=request.query_params.get("audience_type") or "lead_list",
            lead_list_id=request.query_params.get("lead_list"),
            city=request.query_params.get("city") or "",
            opportunity_id=request.query_params.get("opportunity"),
        )
        return Response(payload)


class CampaignAudienceExportView(MarketingModule, APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "marketing.view"

    def get(self, request):
        rows = audience_rows(
            request.tenant,
            audience_type=request.query_params.get("audience_type") or "lead_list",
            lead_list_id=request.query_params.get("lead_list"),
            city=request.query_params.get("city") or "",
            opportunity_id=request.query_params.get("opportunity"),
        )
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="seonet-campaign-audience.csv"'
        writer = csv.writer(response)
        writer.writerow(["name", "email", "phone", "location", "source"])
        for row in rows:
            writer.writerow([row["name"], row["email"], row["phone"], row["location"], row["source"]])
        return response


class CampaignSendView(MarketingModule, APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "marketing.manage"

    def post(self, request, id):
        campaign = Campaign.objects.for_tenant(request.tenant).filter(id=id).first()
        if campaign is None:
            raise APIError("Resource not found.", code="NOT_FOUND", status_code=404)
        if campaign.status == Campaign.Status.SENT:
            raise APIError("This campaign was already recorded as sent.", code="VALIDATION_ERROR")
        preview = audience_count(
            request.tenant,
            audience_type=campaign.audience_type,
            lead_list_id=campaign.lead_list_id,
            city=campaign.city,
            opportunity_id=campaign.opportunity_id,
        )
        campaign.status = Campaign.Status.SENT
        campaign.audience_count = preview["count"]
        campaign.sent_at = timezone.now()
        campaign.send_note = (
            f"Recorded send to {preview['count']} existing audience members. "
            "No email or SMS was dispatched from Seonet."
        )
        campaign.save(update_fields=["status", "audience_count", "sent_at", "send_note", "updated_at"])
        from apps.auditlog.services import write_audit
        from apps.notifications.services import notify
        from apps.usage.services import record_usage

        record_usage(
            tenant=request.tenant,
            user=request.user,
            event_type="campaign_recorded",
            quantity=preview["count"],
            metadata={"campaign_id": str(campaign.id), "audience_type": campaign.audience_type},
        )
        write_audit(
            action="CAMPAIGN_RECORDED",
            request=request,
            tenant=request.tenant,
            resource_type="campaign",
            resource_id=campaign.id,
            metadata={"audience_count": preview["count"]},
        )
        notify(
            tenant=request.tenant,
            user=request.user,
            title=f"Campaign recorded: {campaign.name}",
            body=campaign.send_note,
            kind="success",
            link=f"/app/marketing/{campaign.id}",
        )
        return Response(CampaignSerializer(campaign, context={"request": request}).data)
