from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.billing.entitlements import ensure_billing_catalog
from apps.billing.models import Plan
from apps.users.models import User


@pytest.mark.django_db
def test_tenant_user_cannot_access_platform(api_client, user):
    api_client.force_authenticate(user=user)
    response = api_client.get("/api/v1/platform/overview/")
    assert response.status_code == 403


@pytest.mark.django_db
def test_platform_admin_manages_packages_modules_and_invoices(db):
    ensure_billing_catalog()
    admin = User.objects.create_superuser(email="platform@example.com", password="SecurePass!123")
    tenant_owner = User.objects.create_user(email="acme@example.com", password="SecurePass!123")
    client = APIClient()
    client.force_authenticate(user=admin)

    overview = client.get("/api/v1/platform/overview/")
    assert overview.status_code == 200
    assert overview.data["packages"] >= 4
    assert overview.data["modules"] >= 8

    packages = client.get("/api/v1/platform/packages/")
    assert packages.status_code == 200
    starter = next(item for item in packages.data["results"] if item["code"] == "starter")
    assert "websites" in {module["code"] for module in starter["modules"]}

    from apps.tenants.services import create_tenant_for_owner

    tenant = create_tenant_for_owner(name="Northwind", owner=tenant_owner)
    tenants = client.get("/api/v1/platform/tenants/")
    assert tenants.status_code == 200
    assert any(item["id"] == str(tenant.id) for item in tenants.data["results"])

    growth = Plan.objects.get(code="growth")
    assigned = client.post(f"/api/v1/platform/tenants/{tenant.id}/plan/", {"plan_id": str(growth.id), "status": "active"}, format="json")
    assert assigned.status_code == 200
    assert assigned.data["plan"]["code"] == "growth"

    module_toggle = client.post(
        f"/api/v1/platform/tenants/{tenant.id}/modules/",
        {"module_code": "ai", "is_enabled": True},
        format="json",
    )
    assert module_toggle.status_code == 200
    enabled = {item["code"] for item in module_toggle.data["modules"] if item["is_enabled"]}
    assert "ai" in enabled
    assert "leads" in enabled

    invoice = client.post(
        "/api/v1/platform/invoices/",
        {"tenant_id": str(tenant.id), "description": "Growth plan", "amount": "149.00"},
        format="json",
    )
    assert invoice.status_code == 201
    invoice_id = invoice.data["id"]
    issued = client.post(f"/api/v1/platform/invoices/{invoice_id}/issue/")
    assert issued.data["status"] == "issued"
    paid = client.post(f"/api/v1/platform/invoices/{invoice_id}/mark-paid/")
    assert paid.data["status"] == "paid"

    gateways = client.get("/api/v1/platform/gateways/")
    assert gateways.status_code == 200
    stripe = next(item for item in gateways.data["results"] if item["code"] == "stripe")
    updated = client.patch(f"/api/v1/platform/gateways/{stripe['id']}/", {"is_enabled": True, "test_mode": True}, format="json")
    assert updated.status_code == 200
    assert updated.data["is_enabled"] is True
    assert "encrypted_config" not in updated.data

    created_tenant = client.post(
        "/api/v1/platform/tenants/",
        {
            "name": "Globex",
            "owner_email": "globex@example.com",
            "owner_password": "SecurePass!123",
            "plan_id": str(growth.id),
        },
        format="json",
    )
    assert created_tenant.status_code == 201
    globex_id = created_tenant.data["id"]

    module = client.post("/api/v1/platform/modules/", {"code": "white_label", "name": "White label", "category": "operations"}, format="json")
    assert module.status_code == 201
    feature = client.post(f"/api/v1/platform/modules/{module.data['id']}/features/", {"code": "wl.domain", "name": "Custom domain"}, format="json")
    assert feature.status_code == 201

    custom_plan = client.post(
        "/api/v1/platform/packages/",
        {"code": "custom", "name": "Custom", "price_amount": "10.00", "module_codes": ["websites"]},
        format="json",
    )
    assert custom_plan.status_code == 201
    deleted_plan = client.delete(f"/api/v1/platform/packages/{custom_plan.data['id']}/")
    assert deleted_plan.status_code == 204

    blocked = client.delete(f"/api/v1/platform/packages/{growth.id}/")
    assert blocked.status_code == 409

    draft = client.post(
        "/api/v1/platform/invoices/",
        {"tenant_id": globex_id, "description": "Setup", "amount": "10.00"},
        format="json",
    )
    assert draft.status_code == 201
    edited = client.patch(f"/api/v1/platform/invoices/{draft.data['id']}/", {"amount": "12.00", "description": "Setup fee"}, format="json")
    assert edited.data["total"] == "12.00"
    voided = client.post(f"/api/v1/platform/invoices/{draft.data['id']}/void/")
    assert voided.data["status"] == "void"
    removed = client.delete(f"/api/v1/platform/invoices/{draft.data['id']}/")
    assert removed.status_code == 204

    sub = client.post(
        "/api/v1/platform/subscriptions/",
        {"tenant_id": globex_id, "plan_id": str(growth.id), "status": "active", "seats": 3},
        format="json",
    )
    assert sub.status_code == 201
    canceled = client.delete(f"/api/v1/platform/subscriptions/{sub.data['id']}/")
    assert canceled.status_code == 204

    deleted_tenant = client.delete(f"/api/v1/platform/tenants/{globex_id}/")
    assert deleted_tenant.status_code == 204


@pytest.mark.django_db
def test_platform_admin_updates_appearance(db):
    from io import BytesIO

    from django.core.files.uploadedfile import SimpleUploadedFile
    from PIL import Image
    from rest_framework.test import APIClient

    from apps.users.models import User

    admin = User.objects.create_superuser(email="brand@example.com", password="SecurePass!123")
    client = APIClient()
    client.force_authenticate(user=admin)

    current = client.get("/api/v1/platform/appearance/")
    assert current.status_code == 200
    assert current.data["product_name"] == "Seonet"
    assert current.data["logo_nav_url"] is None
    assert current.data["logo_sidebar_url"] is None
    assert current.data["logo_footer_url"] is None
    assert current.data["logo_mark_url"] is None

    updated = client.patch(
        "/api/v1/platform/appearance/",
        {
            "product_name": "PulseOS",
            "legal_name": "Seonet",
            "tagline": "Growth intelligence",
            "primary_color": "#123456",
            "secondary_color": "#654321",
            "default_theme": "dark",
        },
        format="json",
    )
    assert updated.status_code == 200
    assert updated.data["product_name"] == "PulseOS"
    assert updated.data["primary_color"] == "#123456"

    public = client.get("/api/v1/config/")
    assert public.data["product"] == "PulseOS"
    assert public.data["branding"]["default_theme"] == "dark"

    invalid = client.patch("/api/v1/platform/appearance/", {"primary_color": "navy"}, format="json")
    assert invalid.status_code == 400

    buffer = BytesIO()
    Image.new("RGB", (48, 48), (11, 79, 108)).save(buffer, format="PNG")
    logo = SimpleUploadedFile("logo.png", buffer.getvalue(), content_type="image/png")
    uploaded = client.post("/api/v1/platform/appearance/assets/logo/", {"file": logo}, format="multipart")
    assert uploaded.status_code == 200
    assert uploaded.data["logo_url"]

    nav_buffer = BytesIO()
    Image.new("RGB", (96, 32), (20, 138, 153)).save(nav_buffer, format="PNG")
    nav = SimpleUploadedFile("nav.png", nav_buffer.getvalue(), content_type="image/png")
    nav_uploaded = client.post("/api/v1/platform/appearance/assets/logo_nav/", {"file": nav}, format="multipart")
    assert nav_uploaded.status_code == 200
    assert nav_uploaded.data["logo_nav_url"]
    assert nav_uploaded.data["logo_url"]

    public_branding = client.get("/api/v1/config/").data["branding"]
    assert public_branding["logo_nav_url"]
    assert public_branding["logo_sidebar_url"] is None

    cleared = client.delete("/api/v1/platform/appearance/assets/logo/")
    assert cleared.status_code == 200
    assert cleared.data["logo_url"] is None
    assert cleared.data["logo_nav_url"]

    nav_cleared = client.delete("/api/v1/platform/appearance/assets/logo_nav/")
    assert nav_cleared.status_code == 200
    assert nav_cleared.data["logo_nav_url"] is None
