from __future__ import annotations

from apps.auditlog.models import AuditLog
from apps.common.request_context import get_request_id


def _is_platform_request(request) -> bool:
    path = getattr(request, "path", "") or ""
    return path.startswith("/api/v1/platform/")


def resolve_audit_scope(action: str, *, scope: str | None = None, request=None) -> str:
    if scope in {AuditLog.Scope.WORKSPACE, AuditLog.Scope.PLATFORM}:
        return scope
    if action.startswith("PLATFORM_") or (request is not None and _is_platform_request(request)):
        return AuditLog.Scope.PLATFORM
    return AuditLog.Scope.WORKSPACE


def serialize_activity(item: AuditLog, *, include_tenant: bool = False) -> dict:
    actor = ""
    person = getattr(item, "user", None)
    if person is not None:
        actor = ((person.first_name or "") + " " + (person.last_name or "")).strip() or person.email
    payload = {
        "id": str(item.id),
        "title": item.action.replace("_", " ").title(),
        "action": item.action,
        "actor": actor,
        "created_at": item.created_at.isoformat(),
        "resource_type": item.resource_type,
        "resource_id": item.resource_id,
        "scope": item.scope,
        "metadata": item.metadata or {},
    }
    if include_tenant:
        tenant = getattr(item, "tenant", None)
        payload["tenant_id"] = str(item.tenant_id) if item.tenant_id else ""
        payload["tenant_name"] = tenant.name if tenant is not None else ""
    return payload


def workspace_activity(tenant, *, limit: int = 8):
    return (
        AuditLog.objects.filter(tenant=tenant, scope=AuditLog.Scope.WORKSPACE)
        .select_related("user")
        .order_by("-created_at")[:limit]
    )


def platform_activity(*, limit: int = 8):
    return AuditLog.objects.filter(scope=AuditLog.Scope.PLATFORM).select_related("user").order_by("-created_at")[:limit]


def write_audit(
    *,
    action: str,
    request=None,
    tenant=None,
    user=None,
    resource_type: str = "",
    resource_id: str = "",
    metadata: dict | None = None,
    scope: str | None = None,
) -> None:
    ip = None
    user_agent = ""
    request_id = get_request_id()
    explicit_tenant = tenant
    if request is not None:
        ip = request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR"))
        if ip and "," in ip:
            ip = ip.split(",")[0].strip()
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:512]
        user = user or getattr(request, "user", None)
        if getattr(user, "is_authenticated", False) is False:
            user = None
        if explicit_tenant is None and not _is_platform_request(request):
            tenant = getattr(request, "tenant", None)
        else:
            tenant = explicit_tenant
    resolved_scope = resolve_audit_scope(action, scope=scope, request=request)
    AuditLog.objects.create(
        tenant=tenant,
        user=user,
        scope=resolved_scope,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id else "",
        ip_address=ip or None,
        user_agent=user_agent,
        request_id=request_id,
        metadata=metadata or {},
    )
