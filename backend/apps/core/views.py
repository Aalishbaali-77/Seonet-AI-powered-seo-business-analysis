from __future__ import annotations

import logging

from django.conf import settings
from django.db import connection
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


def _check_database() -> tuple[bool, str]:
    try:
        connection.ensure_connection()
        return True, "ok"
    except Exception as exc:  # noqa: BLE001
        logger.warning("database_health_failed", extra={"error": str(exc)})
        return False, "unavailable"


def _check_redis() -> tuple[bool, str]:
    try:
        from django.core.cache import cache

        cache.set("healthcheck", "ok", 5)
        value = cache.get("healthcheck")
        return value == "ok", "ok" if value == "ok" else "unavailable"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc.__class__.__name__)


def _check_broker() -> tuple[bool, str]:
    try:
        from kombu import Connection

        with Connection(settings.CELERY_BROKER_URL, connect_timeout=2) as conn:
            conn.ensure_connection(max_retries=1, timeout=2)
        return True, "ok"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc.__class__.__name__)


class HealthView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes: list = []

    def get(self, request):
        db_ok, db_msg = _check_database()
        redis_ok, redis_msg = _check_redis()
        broker_ok, broker_msg = _check_broker()
        payload = {
            "status": "ok" if db_ok else "degraded",
            "version": settings.APP_VERSION,
            "checks": {
                "database": {"ok": db_ok, "detail": db_msg},
                "redis": {"ok": redis_ok, "detail": redis_msg},
                "broker": {"ok": broker_ok, "detail": broker_msg},
            },
        }
        return Response(payload, status=status.HTTP_200_OK if db_ok else status.HTTP_503_SERVICE_UNAVAILABLE)


class LiveView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes: list = []

    def get(self, request):
        return Response({"status": "ok"})


class ReadyView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes: list = []

    def get(self, request):
        db_ok, db_msg = _check_database()
        if not db_ok:
            return Response({"status": "not_ready", "database": db_msg}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response({"status": "ready"})


class PublicConfigView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes: list = []

    def get(self, request):
        from apps.billing.entitlements import ensure_billing_catalog
        from apps.billing.models import Plan, ProductModule
        from apps.billing.serializers import PlanSerializer, ProductModuleSerializer
        from apps.platform.models import PlatformAppearance, PlatformLanding
        from apps.platform.serializers import PlatformAppearanceSerializer, PlatformLandingSerializer

        ensure_billing_catalog()
        appearance = PlatformAppearance.get_solo()
        branding = PlatformAppearanceSerializer(appearance, context={"request": request}).data
        landing = PlatformLandingSerializer(PlatformLanding.get_solo()).data
        packages = PlanSerializer(
            Plan.objects.filter(is_active=True, is_public=True).prefetch_related("plan_modules__module"),
            many=True,
        ).data
        modules = ProductModuleSerializer(
            ProductModule.objects.filter(is_active=True),
            many=True,
        ).data
        return Response(
            {
                "product": branding["product_name"],
                "owner": branding["legal_name"],
                "version": settings.APP_VERSION,
                "feature_flags": settings.FEATURE_FLAGS,
                "branding": branding,
                "landing": landing,
                "packages": packages,
                "modules": modules,
            }
        )
