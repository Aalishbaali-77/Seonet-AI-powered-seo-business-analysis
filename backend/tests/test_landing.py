from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.billing.entitlements import ensure_billing_catalog
from apps.billing.models import Plan
from apps.platform.models import PlatformLanding
from apps.users.models import User


@pytest.mark.django_db
def test_public_config_exposes_landing_and_catalog(api_client):
    ensure_billing_catalog()
    response = api_client.get("/api/v1/config/")
    assert response.status_code == 200
    assert response.data["landing"]["pricing_eyebrow"] == "Pricing"
    assert response.data["landing"]["hero_title"]
    assert response.data["branding"]["support_email"] == "hello@siglobalsolutions.com"
    assert response.data["landing"]["nav"][0]["id"] == "product"
    codes = {item["code"] for item in response.data["packages"]}
    assert {"starter", "growth", "scale", "enterprise"} <= codes
    assert any(item["is_featured"] for item in response.data["packages"] if item["code"] == "growth")
    assert any(item["code"] == "websites" for item in response.data["modules"])


@pytest.mark.django_db
def test_platform_admin_updates_landing(db):
    admin = User.objects.create_superuser(email="landing@example.com", password="SecurePass!123")
    client = APIClient()
    client.force_authenticate(user=admin)

    current = client.get("/api/v1/platform/landing/")
    assert current.status_code == 200
    assert current.data["hero_primary_cta"]

    updated = client.patch(
        "/api/v1/platform/landing/",
        {"hero_title": "Operator headline", "nav": [{"id": "pricing", "label": "Plans"}]},
        format="json",
    )
    assert updated.status_code == 200
    assert updated.data["hero_title"] == "Operator headline"
    assert updated.data["nav"] == [{"id": "pricing", "label": "Plans"}]

    public = client.get("/api/v1/config/")
    assert public.data["landing"]["hero_title"] == "Operator headline"

    invalid = client.patch("/api/v1/platform/landing/", {"pains": [{"title": "Missing body"}]}, format="json")
    assert invalid.status_code == 400


@pytest.mark.django_db
def test_hidden_package_is_not_on_public_catalog(db):
    ensure_billing_catalog()
    Plan.objects.filter(code="enterprise").update(is_public=False, is_active=True)
    client = APIClient()
    codes = {item["code"] for item in client.get("/api/v1/config/").data["packages"]}
    assert "enterprise" not in codes
    assert "growth" in codes
    assert PlatformLanding.get_solo().nav


@pytest.mark.django_db
def test_seed_applies_canonical_product_content(db):
    from apps.billing.entitlements import ensure_billing_catalog
    from apps.billing.models import ProductModule
    from apps.platform.content import apply_platform_content

    ensure_billing_catalog(refresh_copy=True)
    appearance, landing = apply_platform_content()
    assert landing.hero_title == "Website intelligence, honest markets, and pipeline in one workspace."
    assert any(item["title"] == "Check keywords" for item in landing.steps)
    assert any("scrape" in item["q"].lower() for item in landing.faqs)
    assert appearance.support_email == "hello@siglobalsolutions.com"
    websites = ProductModule.objects.get(code="websites")
    assert "first-class workspace object" in websites.description
    growth = Plan.objects.get(code="growth")
    assert growth.is_featured
    assert growth.cta_label == "Start Growth"

