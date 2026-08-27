from __future__ import annotations

from django.utils.text import slugify

from apps.rbac.services import assign_role, provision_tenant_roles
from apps.tenants.models import Membership, Tenant
from apps.crm.services import ensure_default_pipeline


def unique_slug(base: str) -> str:
    slug = slugify(base)[:70] or "workspace"
    candidate = slug
    index = 2
    while Tenant.all_objects.filter(slug=candidate).exists():
        candidate = f"{slug}-{index}"
        index += 1
    return candidate


def create_tenant_for_owner(*, name: str, owner) -> Tenant:
    tenant = Tenant.objects.create(name=name, slug=unique_slug(name), status=Tenant.Status.ACTIVE)
    provision_tenant_roles(tenant)
    membership = Membership.objects.create(
        tenant=tenant,
        user=owner,
        is_default=True,
        status=Membership.Status.ACTIVE,
    )
    assign_role(membership, "owner")
    ensure_default_pipeline(tenant)
    from apps.billing.entitlements import apply_plan_to_tenant, ensure_billing_catalog
    from apps.billing.models import Plan

    ensure_billing_catalog()
    plan = Plan.objects.get(code="starter")
    apply_plan_to_tenant(tenant, plan)
    return tenant
