from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from rest_framework.test import APIClient

from apps.leads.models import ICP
from apps.leads.services import confirm_icp, execute_discovery_job, parse_icp_from_text, start_discovery
from apps.platform.lead_sources import build_icp_queries, ensure_lead_sources
from apps.platform.models import LeadSource
from apps.users.models import User


def _source(results, code: str) -> dict:
    return next(item for item in results if item["code"] == code)


@pytest.mark.django_db
def test_platform_admin_stores_places_key_without_echoing_it():
    ensure_lead_sources()
    admin = User.objects.create_superuser(email="platform@example.com", password="SecurePass!123")
    client = APIClient()
    client.force_authenticate(user=admin)
    listed = client.get("/api/v1/platform/lead-sources/")
    assert listed.status_code == 200
    codes = {item["code"] for item in listed.data["results"]}
    assert {
        "google_places",
        "yelp",
        "foursquare",
        "geoapify",
        "openstreetmap",
        "opencorporates",
        "npi_registry",
        "linkedin_sales_navigator",
        "yellowpage_pk",
        "bbb",
        "manta",
        "openai",
        "anthropic",
        "xai",
        "google_gemini",
        "google_pagespeed",
        "google_custom_search",
        "serpapi",
        "hunter",
        "clearbit",
        "apollo",
        "wikidata",
    } <= codes
    source = _source(listed.data["results"], "google_places")
    assert "api_key" not in source
    assert source["credentials_configured"] is False
    assert source["category"] == "discovery"

    updated = client.patch(
        f"/api/v1/platform/lead-sources/{source['id']}/",
        {"api_key": "AIza-secret", "is_enabled": True},
        format="json",
    )
    assert updated.status_code == 200
    assert updated.data["is_enabled"] is True
    assert updated.data["credentials_configured"] is True
    assert "AIza-secret" not in str(updated.data)
    stored = LeadSource.objects.get(id=source["id"])
    assert stored.encrypted_config["api_key"] == "AIza-secret"


@pytest.mark.django_db
def test_platform_admin_stores_openai_key_and_tests_it():
    ensure_lead_sources()
    admin = User.objects.create_superuser(email="platform-ai@example.com", password="SecurePass!123")
    client = APIClient()
    client.force_authenticate(user=admin)
    listed = client.get("/api/v1/platform/lead-sources/")
    source = _source(listed.data["results"], "openai")
    updated = client.patch(
        f"/api/v1/platform/lead-sources/{source['id']}/",
        {"api_key": "sk-secret", "model": "gpt-4o-mini", "is_enabled": True},
        format="json",
    )
    assert updated.status_code == 200
    assert updated.data["category"] == "ai"
    assert updated.data["model"] == "gpt-4o-mini"
    assert "sk-secret" not in str(updated.data)
    mock_response = MagicMock(status_code=200)
    mock_response.json.return_value = {"data": [{"id": "gpt-4o-mini"}, {"id": "gpt-4o"}]}
    with patch("providers.ai.adapters.httpx.Client") as client_cls:
        client_cls.return_value.__enter__.return_value.request.return_value = mock_response
        probed = client.post(f"/api/v1/platform/lead-sources/{source['id']}/test/")
    assert probed.status_code == 200
    assert probed.data["ok"] is True
    assert probed.data["sample_count"] == 2
    assert probed.data["provider"] == "openai"


@pytest.mark.django_db
def test_discovery_uses_platform_places_key(user, tenant):
    from apps.billing.entitlements import apply_plan_to_tenant
    from apps.billing.models import Plan

    apply_plan_to_tenant(tenant, Plan.objects.get(code="growth"), status="active")
    ensure_lead_sources()
    source = LeadSource.objects.get(code="google_places")
    source.encrypted_config = {"api_key": "AIza-test"}
    source.is_enabled = True
    source.save()
    icp = ICP.objects.create(
        tenant=tenant,
        name="Dental",
        raw_input="We sell to dental services providers in Karachi.",
        industry="dental services providers",
        locations=["Karachi"],
        keywords=["dental services providers"],
        status=ICP.Status.CONFIRMED,
    )
    confirm_icp(icp)
    mock_response = MagicMock(status_code=200)
    mock_response.json.return_value = {
        "status": "OK",
        "results": [
            {
                "place_id": "abc123",
                "name": "Clove Dental Karachi",
                "formatted_address": "Clifton, Karachi",
                "types": ["dentist", "health"],
            }
        ],
    }
    with patch("providers.leads.google_places.httpx.Client") as client_cls:
        client_cls.return_value.__enter__.return_value.get.return_value = mock_response
        search = start_discovery(icp=icp, user=user)
        execute_discovery_job(search.job)
    search.refresh_from_db()
    assert search.discovered == 1
    lead = search.leads.get()
    assert lead.company_name == "Clove Dental Karachi"
    assert lead.location == "Clifton, Karachi"
    assert lead.source == "google_places"


@pytest.mark.django_db
def test_icp_query_includes_karachi_dental():
    icp = ICP(industry="dental services providers", locations=["Karachi"], keywords=["dental clinics"])
    assert "dental clinics in Karachi" in build_icp_queries(icp)


@pytest.mark.django_db
def test_icp_parse_uses_enabled_openai(tenant, user):
    ensure_lead_sources()
    source = LeadSource.objects.get(code="openai")
    source.encrypted_config = {"api_key": "sk-test"}
    source.is_enabled = True
    source.save()
    mock_response = MagicMock(status_code=200)
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": '{"industry":"dental services","employee_count":"","locations":["Karachi"],"keywords":["dental clinics"]}'
                }
            }
        ]
    }
    with patch("providers.ai.adapters.httpx.Client") as client_cls:
        client_cls.return_value.__enter__.return_value.request.return_value = mock_response
        parsed = parse_icp_from_text("We sell to dental clinics in Karachi.", tenant=tenant, user=user)
    assert parsed["origin"] == "ai"
    assert parsed["industry"] == "dental services"
    assert "Karachi" in parsed["locations"]


@pytest.mark.django_db
def test_platform_admin_stores_pagespeed_key_without_echoing_it():
    ensure_lead_sources()
    admin = User.objects.create_superuser(email="platform-psi@example.com", password="SecurePass!123")
    client = APIClient()
    client.force_authenticate(user=admin)
    listed = client.get("/api/v1/platform/lead-sources/")
    source = _source(listed.data["results"], "google_pagespeed")
    assert source["category"] == "diagnostics"
    updated = client.patch(
        f"/api/v1/platform/lead-sources/{source['id']}/",
        {"api_key": "AIza-pagespeed", "is_enabled": True},
        format="json",
    )
    assert updated.status_code == 200
    assert updated.data["is_enabled"] is True
    assert "AIza-pagespeed" not in str(updated.data)
    mock_response = MagicMock(status_code=200)
    mock_response.content = b'{"lighthouseResult":{"audits":{}}}'
    mock_response.json.return_value = {"lighthouseResult": {"audits": {}}}
    with patch("apps.audits.browser_ux.httpx.Client") as client_cls:
        client_cls.return_value.__enter__.return_value.get.return_value = mock_response
        probed = client.post(f"/api/v1/platform/lead-sources/{source['id']}/test/")
    assert probed.status_code == 200
    assert probed.data["ok"] is True
    assert probed.data["provider"] == "google_pagespeed"


@pytest.mark.django_db
def test_openstreetmap_can_enable_without_a_key():
    ensure_lead_sources()
    admin = User.objects.create_superuser(email="platform-osm@example.com", password="SecurePass!123")
    client = APIClient()
    client.force_authenticate(user=admin)
    listed = client.get("/api/v1/platform/lead-sources/")
    source = _source(listed.data["results"], "openstreetmap")
    assert source["requires_key"] is False
    assert source["credentials_configured"] is True
    updated = client.patch(f"/api/v1/platform/lead-sources/{source['id']}/", {"is_enabled": True}, format="json")
    assert updated.status_code == 200
    assert updated.data["is_enabled"] is True
    mock_response = MagicMock(status_code=200)
    mock_response.json.return_value = [
        {"osm_id": 1, "class": "amenity", "type": "cafe", "name": "Cafe Aylar", "display_name": "Cafe Aylar, Karachi"}
    ]
    with patch("providers.leads.adapters.httpx.Client") as client_cls:
        client_cls.return_value.__enter__.return_value.get.return_value = mock_response
        probed = client.post(f"/api/v1/platform/lead-sources/{source['id']}/test/")
    assert probed.status_code == 200
    assert probed.data["ok"] is True
    assert probed.data["provider"] == "openstreetmap"


@pytest.mark.django_db
def test_yellowpage_pk_test_requires_licensed_search_url():
    ensure_lead_sources()
    admin = User.objects.create_superuser(email="platform-yp@example.com", password="SecurePass!123")
    client = APIClient()
    client.force_authenticate(user=admin)
    listed = client.get("/api/v1/platform/lead-sources/")
    source = _source(listed.data["results"], "yellowpage_pk")
    updated = client.patch(
        f"/api/v1/platform/lead-sources/{source['id']}/",
        {"api_key": "yp-secret", "is_enabled": True},
        format="json",
    )
    assert updated.status_code == 200
    assert "yp-secret" not in str(updated.data)
    probed = client.post(f"/api/v1/platform/lead-sources/{source['id']}/test/")
    assert probed.status_code >= 400


@pytest.mark.django_db
def test_yelp_discovery_uses_fusion_api(user, tenant):
    from apps.billing.entitlements import apply_plan_to_tenant
    from apps.billing.models import Plan

    apply_plan_to_tenant(tenant, Plan.objects.get(code="growth"), status="active")
    ensure_lead_sources()
    LeadSource.objects.filter(category=LeadSource.Category.DISCOVERY).update(is_enabled=False)
    source = LeadSource.objects.get(code="yelp")
    source.encrypted_config = {"api_key": "yelp-test"}
    source.is_enabled = True
    source.save()
    icp = ICP.objects.create(
        tenant=tenant,
        name="Dental",
        raw_input="We sell to dental clinics in Karachi.",
        industry="dental clinics",
        locations=["Karachi"],
        keywords=["dental clinics"],
        status=ICP.Status.CONFIRMED,
    )
    confirm_icp(icp)
    mock_response = MagicMock(status_code=200)
    mock_response.json.return_value = {
        "businesses": [
            {
                "id": "yelp-1",
                "name": "Clove Dental",
                "url": "https://www.yelp.com/biz/clove",
                "location": {"display_address": ["Clifton", "Karachi"]},
                "categories": [{"title": "Dentists"}],
            }
        ]
    }
    with patch("providers.leads.adapters.httpx.Client") as client_cls:
        client_cls.return_value.__enter__.return_value.get.return_value = mock_response
        search = start_discovery(icp=icp, user=user)
        execute_discovery_job(search.job)
    search.refresh_from_db()
    assert search.discovered == 1
    lead = search.leads.get()
    assert lead.company_name == "Clove Dental"
    assert lead.source == "yelp"
