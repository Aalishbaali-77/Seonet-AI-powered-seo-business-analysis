from __future__ import annotations

from apps.common.request_context import set_tenant_id
from apps.tenants.models import Membership


def resolve_request_tenant(request):
    pinned = getattr(request, "api_token_tenant", None)
    if pinned is not None:
        request.tenant = pinned
        set_tenant_id(str(pinned.id))
        return request.tenant
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        request.tenant = getattr(request, "tenant", None)
        return request.tenant
    tenant_id = request.headers.get("X-Tenant-ID") or request.COOKIES.get("seonet_tenant")
    path = getattr(request, "path", "") or ""
    if path.startswith("/api/v1/platform/"):
        request.tenant = None
        return request.tenant
    memberships = Membership.objects.filter(user=user, status=Membership.Status.ACTIVE).select_related("tenant")
    selected = None
    if tenant_id:
        selected = memberships.filter(tenant_id=tenant_id).first()
    if selected is None:
        selected = memberships.filter(is_default=True).first() or memberships.first()
    request.tenant = selected.tenant if selected is not None else None
    if request.tenant is not None:
        set_tenant_id(str(request.tenant.id))
    return request.tenant


class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.tenant = None
        resolve_request_tenant(request)
        return self.get_response(request)
