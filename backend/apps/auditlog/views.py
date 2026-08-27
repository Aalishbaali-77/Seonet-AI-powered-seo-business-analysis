from django.utils import timezone
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai.capture import client_ip, clip
from apps.auditlog.models import PageView
from apps.common.permissions import HasTenant


class PageViewCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant]
    subscription_exempt = True

    def post(self, request):
        path = clip(request.data.get("path") or request.data.get("href") or "", 512)
        if not path.startswith("/app"):
            return Response({"ok": True, "recorded": False})
        title = clip(request.data.get("title") or "", 160)
        referrer = clip(request.data.get("referrer") or "", 512)
        recent = (
            PageView.objects.for_tenant(request.tenant)
            .filter(user=request.user, path=path)
            .order_by("-created_at")
            .first()
        )
        if recent is not None and (timezone.now() - recent.created_at).total_seconds() < 20:
            return Response({"ok": True, "recorded": False})
        PageView.objects.create(
            tenant=request.tenant,
            user=request.user,
            path=path,
            title=title,
            referrer=referrer,
            ip_address=client_ip(request),
            user_agent=(request.META.get("HTTP_USER_AGENT") or "")[:512],
        )
        return Response({"ok": True, "recorded": True}, status=201)
