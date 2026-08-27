from __future__ import annotations

from apps.rbac.catalog import PERMISSION_CATALOG, ROLE_LABELS, ROLE_PERMISSIONS
from apps.rbac.models import MembershipRole, Permission, Role, RolePermission
from apps.tenants.models import Membership, Tenant


def sync_permission_catalog() -> None:
    for code, name, module in PERMISSION_CATALOG:
        Permission.objects.update_or_create(code=code, defaults={"name": name, "module": module})


def sync_system_roles() -> None:
    sync_permission_catalog()
    all_codes = [code for code, _, _ in PERMISSION_CATALOG]
    for code, label in ROLE_LABELS.items():
        role, _ = Role.objects.get_or_create(
            tenant=None,
            code=code,
            defaults={"name": label, "is_system": True},
        )
        granted = all_codes if ROLE_PERMISSIONS[code] == "*" else ROLE_PERMISSIONS[code]
        permissions = list(Permission.objects.filter(code__in=granted))
        RolePermission.objects.filter(role=role).exclude(permission__in=permissions).delete()
        for permission in permissions:
            RolePermission.objects.get_or_create(role=role, permission=permission)


def provision_tenant_roles(tenant: Tenant) -> dict[str, Role]:
    sync_system_roles()
    cloned: dict[str, Role] = {}
    for template in Role.objects.filter(tenant__isnull=True, is_system=True):
        role, created = Role.objects.get_or_create(
            tenant=tenant,
            code=template.code,
            defaults={"name": template.name, "is_system": True},
        )
        if created or not role.role_permissions.exists():
            RolePermission.objects.filter(role=role).delete()
            for rp in template.role_permissions.select_related("permission"):
                RolePermission.objects.get_or_create(role=role, permission=rp.permission)
        else:
            current = set(role.permissions.values_list("code", flat=True))
            for rp in template.role_permissions.select_related("permission"):
                if rp.permission.code not in current:
                    RolePermission.objects.get_or_create(role=role, permission=rp.permission)
        cloned[role.code] = role
    return cloned


def set_role_permissions(role: Role, codes: list[str]) -> None:
    permissions = list(Permission.objects.filter(code__in=codes))
    found = {item.code for item in permissions}
    missing = [code for code in codes if code not in found]
    if missing:
        from apps.common.exceptions import APIError

        raise APIError(f"Unknown permission: {missing[0]}.", code="VALIDATION_ERROR")
    RolePermission.objects.filter(role=role).exclude(permission__in=permissions).delete()
    for permission in permissions:
        RolePermission.objects.get_or_create(role=role, permission=permission)


def assign_role(membership: Membership, role_code: str) -> None:
    role = Role.objects.filter(tenant=membership.tenant, code=role_code).first()
    if role is None:
        provision_tenant_roles(membership.tenant)
        role = Role.objects.get(tenant=membership.tenant, code=role_code)
    MembershipRole.objects.get_or_create(membership=membership, role=role)


def user_permission_codes(user, tenant: Tenant | None) -> set[str]:
    if user is None or not user.is_authenticated:
        return set()
    if user.is_superuser:
        return {code for code, _, _ in PERMISSION_CATALOG}
    if tenant is None:
        return set()
    membership = (
        Membership.objects.filter(user=user, tenant=tenant, status=Membership.Status.ACTIVE)
        .prefetch_related("membership_roles__role__permissions")
        .first()
    )
    if membership is None:
        return set()
    codes: set[str] = set()
    for membership_role in membership.membership_roles.all():
        if membership_role.role.code in {"owner", "admin"}:
            return {code for code, _, _ in PERMISSION_CATALOG}
        codes.update(membership_role.role.permissions.values_list("code", flat=True))
    return codes


def user_has_permission(user, tenant: Tenant | None, code: str) -> bool:
    return code in user_permission_codes(user, tenant)
