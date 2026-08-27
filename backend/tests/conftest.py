from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.rbac.services import assign_role, provision_tenant_roles
from apps.tenants.models import Membership, Tenant
from apps.users.models import User


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def user(db) -> User:
    return User.objects.create_user(email="owner@example.com", password="SecurePass!123", first_name="Ada")


@pytest.fixture
def tenant(db, user) -> Tenant:
    from apps.billing.entitlements import apply_plan_to_tenant, ensure_billing_catalog
    from apps.billing.models import Plan

    tenant = Tenant.objects.create(name="Acme", slug="acme", status=Tenant.Status.ACTIVE)
    provision_tenant_roles(tenant)
    membership = Membership.objects.create(tenant=tenant, user=user, is_default=True, status=Membership.Status.ACTIVE)
    assign_role(membership, "owner")
    ensure_billing_catalog()
    apply_plan_to_tenant(tenant, Plan.objects.get(code="growth"), status="trialing")
    return tenant


@pytest.fixture
def other_user(db) -> User:
    return User.objects.create_user(email="other@example.com", password="SecurePass!123")


@pytest.fixture
def other_tenant(db, other_user) -> Tenant:
    from apps.billing.entitlements import apply_plan_to_tenant, ensure_billing_catalog
    from apps.billing.models import Plan

    tenant = Tenant.objects.create(name="Beta", slug="beta", status=Tenant.Status.ACTIVE)
    provision_tenant_roles(tenant)
    membership = Membership.objects.create(tenant=tenant, user=other_user, is_default=True, status=Membership.Status.ACTIVE)
    assign_role(membership, "owner")
    ensure_billing_catalog()
    apply_plan_to_tenant(tenant, Plan.objects.get(code="growth"), status="trialing")
    return tenant


@pytest.fixture
def viewer(db, tenant) -> User:
    person = User.objects.create_user(email="viewer@example.com", password="SecurePass!123")
    membership = Membership.objects.create(tenant=tenant, user=person, status=Membership.Status.ACTIVE)
    assign_role(membership, "viewer")
    return person
