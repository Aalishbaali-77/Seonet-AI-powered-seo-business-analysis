from __future__ import annotations

import pytest

from apps.auditlog.models import AuditLog
from apps.tenants.models import Membership
from apps.users.models import User


@pytest.mark.django_db
def test_register_creates_tenant_and_owner(api_client):
    response = api_client.post(
        "/api/v1/auth/register/",
        {
            "email": "new@example.com",
            "password": "SecurePass!123",
            "first_name": "New",
            "company_name": "Northwind",
        },
        format="json",
    )
    assert response.status_code == 201
    user = User.objects.get(email="new@example.com")
    assert user.memberships.count() == 1
    membership = user.memberships.get()
    assert membership.membership_roles.filter(role__code="owner").exists()
    assert "sipulse_access" in response.cookies
    assert AuditLog.objects.filter(action="TENANT_CREATED").exists()


@pytest.mark.django_db
def test_login_and_me(api_client, user, tenant):
    response = api_client.post(
        "/api/v1/auth/login/",
        {"email": "owner@example.com", "password": "SecurePass!123"},
        format="json",
    )
    assert response.status_code == 200
    me = api_client.get("/api/v1/auth/me/", HTTP_X_TENANT_ID=str(tenant.id))
    assert me.status_code == 200
    assert me.data["email"] == "owner@example.com"
    assert "settings.manage" in me.data["permissions"]
    assert AuditLog.objects.filter(action="USER_LOGIN").exists()


@pytest.mark.django_db
def test_cors_preflight_allows_tenant_header(api_client):
    response = api_client.options(
        "/api/v1/config/",
        HTTP_ORIGIN="http://localhost:3000",
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
        HTTP_ACCESS_CONTROL_REQUEST_HEADERS="x-tenant-id",
    )
    assert response.status_code in {200, 204}
    allowed = (response.get("Access-Control-Allow-Headers") or "").lower()
    assert "x-tenant-id" in allowed
    assert response.get("Access-Control-Allow-Origin") == "http://localhost:3000"


@pytest.mark.django_db
def test_login_rejects_bad_password(api_client, user):
    response = api_client.post(
        "/api/v1/auth/login/",
        {"email": "owner@example.com", "password": "wrong-password"},
        format="json",
    )
    assert response.status_code == 401
    assert response.data["error"]["code"] == "UNAUTHENTICATED"
