from django.db.models import Sum
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import HasPermissionCode, HasTenant
from apps.usage.models import UsageRecord
from apps.usage.serializers import UsageRecordSerializer


class UsageListView(generics.ListAPIView):
    serializer_class = UsageRecordSerializer
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "billing.view"
    filterset_fields = ("event_type",)

    def get_queryset(self):
        return UsageRecord.objects.for_tenant(self.request.tenant)


class UsageSummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "billing.view"

    def get(self, request):
        qs = UsageRecord.objects.for_tenant(request.tenant)
        grouped = qs.values("event_type").annotate(total=Sum("quantity")).order_by("event_type")
        return Response({"events": list(grouped), "count": qs.count()})
