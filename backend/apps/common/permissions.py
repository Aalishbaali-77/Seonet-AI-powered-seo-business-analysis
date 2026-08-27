from rest_framework.permissions import BasePermission

from apps.common.exceptions import FeatureDisabled, TenantRequired


class HasTenant(BasePermission):
    def has_permission(self, request, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        from apps.tenants.middleware import resolve_request_tenant

        tenant = getattr(request, "tenant", None) or resolve_request_tenant(request)
        if tenant is None:
            raise TenantRequired("Select an active tenant.")
        if not getattr(view, "subscription_exempt", False):
            from apps.billing.entitlements import assert_subscription_access

            assert_subscription_access(tenant)
        module = getattr(view, "required_module", None)
        if module:
            from apps.billing.entitlements import tenant_module_codes

            if module not in tenant_module_codes(tenant):
                raise FeatureDisabled(
                    f"The {module} module is not assigned to this workspace.",
                    details={"module": module, "redirect": "/app/billing"},
                )
        return True


class HasPermissionCode(BasePermission):
    def has_permission(self, request, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        code = getattr(view, "required_permission", None)
        if code is None:
            return True
        tenant = getattr(request, "tenant", None)
        if tenant is None:
            from apps.tenants.middleware import resolve_request_tenant

            tenant = resolve_request_tenant(request)
        from apps.rbac.services import user_has_permission

        return user_has_permission(request.user, tenant, code)
