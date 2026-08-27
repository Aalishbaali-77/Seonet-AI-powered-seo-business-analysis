from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import HasTenant
from apps.notifications.models import Notification
from apps.notifications.serializers import NotificationSerializer


class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated, HasTenant]
    subscription_exempt = True

    def get_queryset(self):
        return Notification.objects.for_tenant(self.request.tenant).filter(user=self.request.user)


class NotificationReadView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant]
    subscription_exempt = True

    def post(self, request, id):
        notification = Notification.objects.for_tenant(request.tenant).filter(user=request.user, id=id).first()
        if notification is None:
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
        notification.read_at = timezone.now()
        notification.save(update_fields=["read_at", "updated_at"])
        return Response(NotificationSerializer(notification).data)


class NotificationReadAllView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant]
    subscription_exempt = True

    def post(self, request):
        now = timezone.now()
        updated = (
            Notification.objects.for_tenant(request.tenant)
            .filter(user=request.user, read_at__isnull=True)
            .update(read_at=now, updated_at=now)
        )
        return Response({"updated": updated})
