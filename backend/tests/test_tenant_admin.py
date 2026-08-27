from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.tenants.models import Membership
from apps.users.models import User


@pytest.mark.django_db
def test_register_is_minimal_and_makes_owner(api_client):
    response = api_client.post(
        "/api/v1/auth/register/",
        {"email": "founder@northwind.example", "password": "SecurePass!123", "name": "Amina Rahman"},
        format="json",
    )
    assert response.status_code == 201
    user = User.objects.get(email="founder@northwind.example")
    assert user.first_name == "Amina"
    assert user.last_name == "Rahman"
    membership = user.memberships.get()
    assert membership.membership_roles.filter(role__code="owner").exists()
    assert membership.tenant.name == "Northwind"


@pytest.mark.django_db
def test_owner_manages_members_roles_and_permissions(api_client, user, tenant):
    api_client.force_authenticate(user=user)
    headers = {"HTTP_X_TENANT_ID": str(tenant.id)}

    invited = api_client.post(
        f"/api/v1/tenants/{tenant.id}/members/",
        {"email": "analyst@acme.test", "first_name": "Sam", "role_code": "analyst", "password": "SecurePass!123"},
        format="json",
        **headers,
    )
    assert invited.status_code == 201
    assert invited.data["roles"] == ["analyst"]
    member_id = invited.data["id"]

    created_role = api_client.post(
        "/api/v1/roles/",
        {"name": "Auditors", "permission_codes": ["website.view", "website.audit", "job.view"]},
        format="json",
        **headers,
    )
    assert created_role.status_code == 201
    assert "website.audit" in created_role.data["permissions"]

    updated = api_client.patch(
        f"/api/v1/tenants/{tenant.id}/members/{member_id}/",
        {"role_code": created_role.data["code"]},
        format="json",
        **headers,
    )
    assert updated.status_code == 200
    assert created_role.data["code"] in updated.data["roles"]

    owner_role = next(item for item in api_client.get("/api/v1/roles/", **headers).data if item["code"] == "owner")
    locked = api_client.patch(f"/api/v1/roles/{owner_role['id']}/", {"name": "Hacked"}, format="json", **headers)
    assert locked.status_code == 400


@pytest.mark.django_db
def test_viewer_cannot_manage_members(api_client, tenant, viewer):
    api_client.force_authenticate(user=viewer)
    response = api_client.post(
        f"/api/v1/tenants/{tenant.id}/members/",
        {"email": "new@acme.test", "role_code": "viewer"},
        format="json",
        HTTP_X_TENANT_ID=str(tenant.id),
    )
    assert response.status_code == 403
    assert Membership.objects.filter(tenant=tenant).count() == 2
