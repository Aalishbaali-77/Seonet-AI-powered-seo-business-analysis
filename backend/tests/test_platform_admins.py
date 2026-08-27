from __future__ import annotations

import pytest
from django.core import mail

from apps.common.exceptions import APIError
from apps.users.models import User


@pytest.mark.django_db
def test_tenant_user_cannot_list_platform_admins(api_client, user):
    api_client.force_authenticate(user=user)
    response = api_client.get("/api/v1/platform/admins/")
    assert response.status_code == 403


@pytest.mark.django_db
def test_platform_admin_lists_admins_without_password_field(api_client):
    admin = User.objects.create_superuser(email="owner@sigbl.com", password="SecurePass!123")
    api_client.force_authenticate(user=admin)
    response = api_client.get("/api/v1/platform/admins/")
    assert response.status_code == 200
    row = next(item for item in response.data["results"] if item["email"] == "owner@sigbl.com")
    assert "password" not in row
    assert row["is_active"] is True
    assert row["last_login"] is None


@pytest.mark.django_db
def test_invite_creates_admin_with_unusable_password_and_sends_email(api_client):
    admin = User.objects.create_superuser(email="owner@sigbl.com", password="SecurePass!123")
    api_client.force_authenticate(user=admin)
    response = api_client.post(
        "/api/v1/platform/admins/",
        {"email": "new-admin@sigbl.com", "first_name": "Jordan", "last_name": "Lee"},
        format="json",
    )
    assert response.status_code == 201
    assert "password" not in response.data
    created = User.objects.get(email="new-admin@sigbl.com")
    assert created.is_staff is True
    assert created.is_superuser is False
    assert created.has_usable_password() is False
    assert len(mail.outbox) == 1
    assert "new-admin@sigbl.com" in mail.outbox[0].to
    assert "password" not in mail.outbox[0].body.lower() or "set your password" in mail.outbox[0].body.lower()


@pytest.mark.django_db
def test_invite_rejects_existing_platform_admin(api_client):
    admin = User.objects.create_superuser(email="owner@sigbl.com", password="SecurePass!123")
    api_client.force_authenticate(user=admin)
    response = api_client.post("/api/v1/platform/admins/", {"email": "owner@sigbl.com"}, format="json")
    assert response.status_code == 409


@pytest.mark.django_db
def test_suspend_and_reactivate_admin(api_client):
    admin = User.objects.create_superuser(email="owner@sigbl.com", password="SecurePass!123")
    other = User.objects.create_user(email="other-admin@sigbl.com", password="SecurePass!123", is_staff=True)
    api_client.force_authenticate(user=admin)

    suspended = api_client.patch(f"/api/v1/platform/admins/{other.id}/", {"is_active": False}, format="json")
    assert suspended.status_code == 200
    assert suspended.data["is_active"] is False
    other.refresh_from_db()
    assert other.is_active is False

    reactivated = api_client.patch(f"/api/v1/platform/admins/{other.id}/", {"is_active": True}, format="json")
    assert reactivated.status_code == 200
    assert reactivated.data["is_active"] is True


@pytest.mark.django_db
def test_cannot_suspend_self(api_client):
    admin = User.objects.create_superuser(email="owner@sigbl.com", password="SecurePass!123")
    User.objects.create_user(email="other-admin@sigbl.com", password="SecurePass!123", is_staff=True)
    api_client.force_authenticate(user=admin)
    response = api_client.patch(f"/api/v1/platform/admins/{admin.id}/", {"is_active": False}, format="json")
    assert response.status_code == 400
    admin.refresh_from_db()
    assert admin.is_active is True


@pytest.mark.django_db
def test_suspending_one_of_several_active_admins_is_allowed(api_client):
    admin = User.objects.create_superuser(email="owner@sigbl.com", password="SecurePass!123")
    other = User.objects.create_user(email="other-admin@sigbl.com", password="SecurePass!123", is_staff=True)
    api_client.force_authenticate(user=other)
    response = api_client.patch(f"/api/v1/platform/admins/{admin.id}/", {"is_active": False}, format="json")
    assert response.status_code == 200
    admin.refresh_from_db()
    assert admin.is_active is False


@pytest.mark.django_db
def test_set_platform_admin_active_guards_the_last_active_admin_directly():
    # The last-active-admin guard can only fire when the target is the sole
    # active admin, which the API can never reach: JWTAuthentication requires
    # is_active=True, so the acting user is always active and thus always
    # counted as a remaining admin. This defense-in-depth guard exists for
    # direct/internal callers (e.g. a future management command), so it's
    # exercised at the function level instead of through the API.
    from apps.platform.admins import set_platform_admin_active

    admin = User.objects.create_superuser(email="owner@sigbl.com", password="SecurePass!123")
    with pytest.raises(APIError):
        set_platform_admin_active(admin=admin, actor=None, is_active=False)
    admin.refresh_from_db()
    assert admin.is_active is True


@pytest.mark.django_db
def test_remove_admin_deactivates_and_strips_admin_flags(api_client):
    admin = User.objects.create_superuser(email="owner@sigbl.com", password="SecurePass!123")
    other = User.objects.create_user(email="other-admin@sigbl.com", password="SecurePass!123", is_staff=True)
    api_client.force_authenticate(user=admin)
    response = api_client.delete(f"/api/v1/platform/admins/{other.id}/")
    assert response.status_code == 204
    other.refresh_from_db()
    assert other.is_active is False
    assert other.is_staff is False
    assert other.is_superuser is False
    assert User.objects.filter(id=other.id).exists()


@pytest.mark.django_db
def test_cannot_remove_self(api_client):
    admin = User.objects.create_superuser(email="owner@sigbl.com", password="SecurePass!123")
    User.objects.create_user(email="other-admin@sigbl.com", password="SecurePass!123", is_staff=True)
    api_client.force_authenticate(user=admin)
    response = api_client.delete(f"/api/v1/platform/admins/{admin.id}/")
    assert response.status_code == 400
    admin.refresh_from_db()
    assert admin.is_active is True


@pytest.mark.django_db
def test_removing_one_of_several_active_admins_is_allowed(api_client):
    admin = User.objects.create_superuser(email="owner@sigbl.com", password="SecurePass!123")
    other = User.objects.create_user(email="other-admin@sigbl.com", password="SecurePass!123", is_staff=True)
    api_client.force_authenticate(user=other)
    response = api_client.delete(f"/api/v1/platform/admins/{admin.id}/")
    assert response.status_code == 204
    admin.refresh_from_db()
    assert admin.is_active is False


@pytest.mark.django_db
def test_remove_platform_admin_guards_the_last_active_admin_directly():
    from apps.platform.admins import remove_platform_admin

    admin = User.objects.create_superuser(email="owner@sigbl.com", password="SecurePass!123")
    with pytest.raises(APIError):
        remove_platform_admin(admin=admin, actor=None)
    admin.refresh_from_db()
    assert admin.is_active is True


@pytest.mark.django_db
def test_force_password_reset_sends_email_and_never_returns_password(api_client):
    admin = User.objects.create_superuser(email="owner@sigbl.com", password="SecurePass!123")
    other = User.objects.create_user(email="other-admin@sigbl.com", password="SecurePass!123", is_staff=True)
    api_client.force_authenticate(user=admin)
    response = api_client.post(f"/api/v1/platform/admins/{other.id}/reset-password/")
    assert response.status_code == 200
    assert "password" not in {k for k in response.data if k != "ok"}
    assert len(mail.outbox) == 1
    assert "other-admin@sigbl.com" in mail.outbox[0].to
    assert "SecurePass" not in mail.outbox[0].body


@pytest.mark.django_db
def test_tenant_admin_cannot_manage_platform_admins(api_client, user, tenant):
    from apps.rbac.services import assign_role

    membership = user.memberships.first()
    assign_role(membership, "admin")
    other = User.objects.create_user(email="other-admin@sigbl.com", password="SecurePass!123", is_staff=True)
    api_client.force_authenticate(user=user)
    assert api_client.get("/api/v1/platform/admins/").status_code == 403
    assert api_client.post("/api/v1/platform/admins/", {"email": "x@sigbl.com"}, format="json").status_code == 403
    assert api_client.patch(f"/api/v1/platform/admins/{other.id}/", {"is_active": False}, format="json").status_code == 403
    assert api_client.delete(f"/api/v1/platform/admins/{other.id}/").status_code == 403
