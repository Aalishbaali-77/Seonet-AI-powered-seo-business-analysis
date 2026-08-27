from rest_framework import generics
from rest_framework.filters import SearchFilter, OrderingFilter

from apps.ai.models import AIRequest, AskQuery
from apps.auditlog.models import AuditLog, PageView
from apps.auditlog.services import serialize_activity
from apps.platform.permissions import IsPlatformAdmin
from apps.platform.telemetry_serializers import AskQuerySerializer, PageViewSerializer, PromptLogSerializer
from rest_framework.response import Response
from rest_framework.views import APIView


def _tenant_filter(queryset, request):
    tenant_id = (request.query_params.get("tenant_id") or "").strip()
    if tenant_id:
        return queryset.filter(tenant_id=tenant_id)
    return queryset


class PlatformPromptListView(generics.ListAPIView):
    permission_classes = [IsPlatformAdmin]
    serializer_class = PromptLogSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ("prompt", "untrusted_input", "task", "provider", "tenant__name", "user__email")
    ordering_fields = ("created_at", "prompt_tokens", "completion_tokens")
    ordering = ("-created_at",)

    def get_queryset(self):
        qs = AIRequest.objects.select_related("tenant", "user").all()
        qs = _tenant_filter(qs, self.request)
        task = (self.request.query_params.get("task") or "").strip()
        if task:
            qs = qs.filter(task=task)
        provider = (self.request.query_params.get("provider") or "").strip()
        if provider:
            qs = qs.filter(provider=provider)
        return qs


class PlatformAskListView(generics.ListAPIView):
    permission_classes = [IsPlatformAdmin]
    serializer_class = AskQuerySerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ("question", "intent", "origin", "tenant__name", "user__email")
    ordering_fields = ("created_at",)
    ordering = ("-created_at",)

    def get_queryset(self):
        return _tenant_filter(AskQuery.objects.select_related("tenant", "user").all(), self.request)


class PlatformPageViewListView(generics.ListAPIView):
    permission_classes = [IsPlatformAdmin]
    serializer_class = PageViewSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ("path", "title", "tenant__name", "user__email")
    ordering_fields = ("created_at",)
    ordering = ("-created_at",)

    def get_queryset(self):
        qs = _tenant_filter(PageView.objects.select_related("tenant", "user").all(), self.request)
        path = (self.request.query_params.get("path") or "").strip()
        if path:
            qs = qs.filter(path__icontains=path)
        return qs


class PlatformWorkspaceActivityView(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        qs = AuditLog.objects.select_related("tenant", "user").order_by("-created_at")
        tenant_id = (request.query_params.get("tenant_id") or "").strip()
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)
        scope = (request.query_params.get("scope") or "").strip()
        if scope:
            qs = qs.filter(scope=scope)
        action = (request.query_params.get("action") or "").strip()
        if action:
            qs = qs.filter(action=action)
        limit = min(int(request.query_params.get("page_size") or 50), 100)
        rows = [serialize_activity(item, include_tenant=True) for item in qs[:limit]]
        return Response({"count": qs.count(), "results": rows})
