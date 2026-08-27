from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.auditlog.services import write_audit
from apps.billing.entitlements import tenant_module_codes
from apps.common.permissions import HasPermissionCode, HasTenant
from apps.integrations.catalog import PROVIDER_BY_CODE, WEBHOOK_EVENTS
from apps.integrations.services import (
    disconnect_integration,
    list_integrations,
    rotate_webhook_secret,
    save_integration,
    serialize_connection,
    test_integration,
)
from apps.integrations.tokens import create_api_token, revoke_api_token
from apps.integrations.models import TenantApiToken


class IntegrationListView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "integration.view"

    def get(self, request):
        return Response({"items": list_integrations(request.tenant), "webhook_events": WEBHOOK_EVENTS})


class IntegrationDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "integration.configure"

    def put(self, request, provider: str):
        connection, revealed = save_integration(request.tenant, provider, request.data if isinstance(request.data, dict) else {})
        write_audit(
            action="INTEGRATION_CONFIGURED",
            request=request,
            tenant=request.tenant,
            resource_type="integration",
            resource_id=connection.id,
            metadata={"provider": provider},
        )
        spec = PROVIDER_BY_CODE[provider]
        payload = serialize_connection(spec, connection, modules=tenant_module_codes(request.tenant))
        if revealed:
            payload["revealed"] = revealed
        return Response(payload)

    def delete(self, request, provider: str):
        connection = disconnect_integration(request.tenant, provider)
        write_audit(
            action="INTEGRATION_DISCONNECTED",
            request=request,
            tenant=request.tenant,
            resource_type="integration",
            resource_id=connection.id,
            metadata={"provider": provider},
        )
        spec = PROVIDER_BY_CODE[provider]
        return Response(serialize_connection(spec, connection, modules=tenant_module_codes(request.tenant)))


class IntegrationTestView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "integration.configure"

    def post(self, request, provider: str):
        connection = test_integration(request.tenant, provider)
        write_audit(
            action="INTEGRATION_TESTED",
            request=request,
            tenant=request.tenant,
            resource_type="integration",
            resource_id=connection.id,
            metadata={"provider": provider, "status": connection.status},
        )
        spec = PROVIDER_BY_CODE[provider]
        return Response(serialize_connection(spec, connection, modules=tenant_module_codes(request.tenant)))


class IntegrationSyncView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "integration.configure"

    def post(self, request, provider: str):
        from apps.business.stores import COMMERCE_PROVIDERS
        from apps.business.sync import start_store_sync
        from apps.common.exceptions import APIError
        from apps.jobs.serializers import JobSerializer

        if provider not in COMMERCE_PROVIDERS:
            raise APIError("Only store connections can be synced.", code="VALIDATION_ERROR")
        job = start_store_sync(tenant=request.tenant, user=request.user, provider=provider)
        write_audit(
            action="COMMERCE_SYNC_STARTED",
            request=request,
            tenant=request.tenant,
            resource_type="integration",
            metadata={"provider": provider, "job_id": str(job.id)},
        )
        return Response(JobSerializer(job).data, status=status.HTTP_202_ACCEPTED)


class WebhookRotateView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "integration.configure"

    def post(self, request):
        connection, secret = rotate_webhook_secret(request.tenant)
        write_audit(action="WEBHOOK_SECRET_ROTATED", request=request, tenant=request.tenant, resource_type="integration", resource_id=connection.id)
        spec = PROVIDER_BY_CODE["webhook"]
        payload = serialize_connection(spec, connection, modules=tenant_module_codes(request.tenant))
        payload["revealed"] = {"signing_secret": secret}
        return Response(payload)


def _token_payload(token: TenantApiToken, *, secret: str | None = None) -> dict:
    payload = {
        "id": str(token.id),
        "name": token.name,
        "prefix": token.prefix,
        "last_used_at": token.last_used_at.isoformat() if token.last_used_at else None,
        "created_at": token.created_at.isoformat(),
        "revoked_at": token.revoked_at.isoformat() if token.revoked_at else None,
    }
    if secret:
        payload["token"] = secret
    return payload


class TenantApiTokenListView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "settings.manage"
    subscription_exempt = True

    def get(self, request, id):
        if str(request.tenant.id) != str(id):
            return Response(status=status.HTTP_404_NOT_FOUND)
        tokens = TenantApiToken.objects.for_tenant(request.tenant).filter(revoked_at__isnull=True)
        return Response([_token_payload(item) for item in tokens])

    def post(self, request, id):
        if str(request.tenant.id) != str(id):
            return Response(status=status.HTTP_404_NOT_FOUND)
        name = (request.data or {}).get("name") if isinstance(request.data, dict) else ""
        try:
            token, raw = create_api_token(tenant=request.tenant, user=request.user, name=str(name or ""))
        except ValueError as exc:
            from apps.common.exceptions import APIError

            raise APIError(str(exc), code="VALIDATION_ERROR") from exc
        write_audit(action="API_TOKEN_CREATED", request=request, tenant=request.tenant, resource_type="api_token", resource_id=token.id)
        return Response(_token_payload(token, secret=raw), status=status.HTTP_201_CREATED)


class TenantApiTokenDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasTenant, HasPermissionCode]
    required_permission = "settings.manage"
    subscription_exempt = True

    def delete(self, request, id, token_id):
        if str(request.tenant.id) != str(id):
            return Response(status=status.HTTP_404_NOT_FOUND)
        token = TenantApiToken.objects.for_tenant(request.tenant).filter(id=token_id).first()
        if token is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        revoke_api_token(token)
        write_audit(action="API_TOKEN_REVOKED", request=request, tenant=request.tenant, resource_type="api_token", resource_id=token.id)
        return Response(status=status.HTTP_204_NO_CONTENT)
