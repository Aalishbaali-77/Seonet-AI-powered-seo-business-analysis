from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from rest_framework.test import APIClient

from apps.billing.entitlements import ensure_billing_catalog, set_tenant_module
from apps.billing.models import ProductModule
from apps.integrations.models import CRMConnection, TenantApiToken


def _enable_integrations(tenant):
    ensure_billing_catalog()
    module = ProductModule.objects.get(code="integrations")
    set_tenant_module(tenant, module, enabled=True)


@pytest.mark.django_db
def test_workspace_profile_saves_and_rejects_feature_flags(api_client, user, tenant):
    api_client.force_authenticate(user=user)
    headers = {"HTTP_X_TENANT_ID": str(tenant.id)}
    updated = api_client.patch(
        f"/api/v1/tenants/{tenant.id}/",
        {"name": "Acme Growth", "timezone": "Asia/Karachi", "currency": "PKR", "feature_flags": {"HUBSPOT_ENABLED": True}},
        format="json",
        **headers,
    )
    assert updated.status_code == 200
    assert updated.data["name"] == "Acme Growth"
    assert updated.data["timezone"] == "Asia/Karachi"
    assert updated.data["currency"] == "PKR"
    assert "feature_flags" not in updated.data
    tenant.refresh_from_db()
    assert tenant.feature_flags == {}


@pytest.mark.django_db
def test_hubspot_credentials_are_write_only_and_test_is_real(api_client, user, tenant):
    _enable_integrations(tenant)
    api_client.force_authenticate(user=user)
    headers = {"HTTP_X_TENANT_ID": str(tenant.id)}
    saved = api_client.put("/api/v1/integrations/hubspot/", {"access_token": "pat-secret-value"}, format="json", **headers)
    assert saved.status_code == 200
    assert saved.data["credentials_configured"] is True
    assert saved.data["status"] == "configured"
    assert "pat-secret-value" not in str(saved.data)
    connection = CRMConnection.objects.get(tenant=tenant, provider="hubspot")
    assert connection.encrypted_config["access_token"] == "pat-secret-value"

    listed = api_client.get("/api/v1/integrations/", **headers)
    assert listed.status_code == 200
    hubspot = next(item for item in listed.data["items"] if item["code"] == "hubspot")
    assert "access_token" not in hubspot["config"]
    assert hubspot["credentials_configured"] is True

    mock_response = MagicMock(status_code=200)
    with patch("apps.integrations.probes.httpx.Client") as client_cls:
        client_cls.return_value.__enter__.return_value.get.return_value = mock_response
        tested = api_client.post("/api/v1/integrations/hubspot/test/", **headers)
    assert tested.status_code == 200
    assert tested.data["status"] == "connected"


@pytest.mark.django_db
def test_custom_api_rejects_private_url(api_client, user, tenant):
    _enable_integrations(tenant)
    api_client.force_authenticate(user=user)
    response = api_client.put(
        "/api/v1/integrations/custom_api/",
        {"base_url": "http://127.0.0.1/", "api_key": "secret"},
        format="json",
        HTTP_X_TENANT_ID=str(tenant.id),
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_integrations_locked_without_module(api_client, user, tenant):
    api_client.force_authenticate(user=user)
    listed = api_client.get("/api/v1/integrations/", HTTP_X_TENANT_ID=str(tenant.id))
    hubspot = next(item for item in listed.data["items"] if item["code"] == "hubspot")
    assert hubspot["locked"] is True
    denied = api_client.put(
        "/api/v1/integrations/hubspot/",
        {"access_token": "pat-x"},
        format="json",
        HTTP_X_TENANT_ID=str(tenant.id),
    )
    assert denied.status_code == 403


@pytest.mark.django_db
def test_api_token_shown_once_and_authenticates(api_client, user, tenant):
    api_client.force_authenticate(user=user)
    headers = {"HTTP_X_TENANT_ID": str(tenant.id)}
    created = api_client.post(f"/api/v1/tenants/{tenant.id}/api-tokens/", {"name": "ERP"}, format="json", **headers)
    assert created.status_code == 201
    raw = created.data["token"]
    assert raw.startswith("sip_live_")
    listed = api_client.get(f"/api/v1/tenants/{tenant.id}/api-tokens/", **headers)
    assert "token" not in listed.data[0]

    anon = APIClient()
    overview = anon.get("/api/v1/dashboard/overview/", HTTP_AUTHORIZATION=f"Bearer {raw}")
    assert overview.status_code == 200

    hashed = TenantApiToken.objects.get(id=created.data["id"]).hashed_key
    assert hashed != raw


@pytest.mark.django_db
def test_google_sheets_parses_json_and_hides_key(api_client, user, tenant):
    _enable_integrations(tenant)
    api_client.force_authenticate(user=user)
    headers = {"HTTP_X_TENANT_ID": str(tenant.id)}
    saved = api_client.put(
        "/api/v1/integrations/google_sheets/",
        {
            "spreadsheet_id": "https://docs.google.com/spreadsheets/d/1AbCdEfGhIjKlMnOpQrStUvWxYz1234567890/edit",
            "service_account_json": '{"type":"service_account","client_email":"seonet-sheets@demo.iam.gserviceaccount.com","private_key":"-----BEGIN PRIVATE KEY-----\\nMIIE\\n-----END PRIVATE KEY-----\\n"}',
            "push_leads": True,
            "push_results": True,
        },
        format="json",
        **headers,
    )
    assert saved.status_code == 200, saved.data
    assert saved.data["config"]["spreadsheet_id"] == "1AbCdEfGhIjKlMnOpQrStUvWxYz1234567890"
    assert saved.data["config"]["client_email"] == "seonet-sheets@demo.iam.gserviceaccount.com"
    assert "private_key" not in saved.data["config"]
    assert "BEGIN PRIVATE KEY" not in str(saved.data)
    assert saved.data["setup_steps"]
    connection = CRMConnection.objects.get(tenant=tenant, provider="google_sheets")
    assert "BEGIN PRIVATE KEY" in connection.encrypted_config["private_key"]
    assert "service_account_json" not in connection.encrypted_config

    listed = api_client.get("/api/v1/integrations/", **headers)
    sheets = next(item for item in listed.data["items"] if item["code"] == "google_sheets")
    assert "audit.completed" in listed.data["webhook_events"]
    assert sheets["config"]["client_email"] == "seonet-sheets@demo.iam.gserviceaccount.com"

    mock_response = MagicMock(status_code=200)
    mock_response.json.return_value = {"spreadsheetId": "1AbCdEfGhIjKlMnOpQrStUvWxYz1234567890", "access_token": "ya29.x"}
    with patch("apps.integrations.google.google_access_token", return_value="ya29.x"):
        with patch("apps.integrations.probes.httpx.Client") as client_cls:
            client_cls.return_value.__enter__.return_value.get.return_value = mock_response
            tested = api_client.post("/api/v1/integrations/google_sheets/test/", **headers)
    assert tested.status_code == 200
    assert tested.data["status"] == "connected"


@pytest.mark.django_db
def test_google_sheets_rejects_invalid_json(api_client, user, tenant):
    _enable_integrations(tenant)
    api_client.force_authenticate(user=user)
    response = api_client.put(
        "/api/v1/integrations/google_sheets/",
        {"spreadsheet_id": "1AbCdEfGhIjKlMnOpQrStUvWxYz1234567890", "service_account_json": "not-json"},
        format="json",
        HTTP_X_TENANT_ID=str(tenant.id),
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_lead_create_pushes_to_hubspot_and_survives_provider_errors(api_client, user, tenant):
    _enable_integrations(tenant)
    api_client.force_authenticate(user=user)
    headers = {"HTTP_X_TENANT_ID": str(tenant.id)}
    api_client.put("/api/v1/integrations/hubspot/", {"access_token": "pat-secret-value"}, format="json", **headers)

    created_company = MagicMock(status_code=201)
    created_company.json.return_value = {"id": "123"}
    mock_client = MagicMock()
    mock_client.post.return_value = created_company
    with patch("apps.integrations.probes.httpx.Client") as client_cls:
        client_cls.return_value.__enter__.return_value = mock_client
        created = api_client.post("/api/v1/leads/", {"company_name": "Northwind", "website": "https://northwind.test"}, format="json", **headers)
    assert created.status_code == 201
    assert created.data["crm_synced"] is True
    connection = CRMConnection.objects.get(tenant=tenant, provider="hubspot")
    assert connection.records_synced == 1
    assert mock_client.post.call_count >= 1

    failing = MagicMock(status_code=500)
    mock_fail = MagicMock()
    mock_fail.post.return_value = failing
    with patch("apps.integrations.probes.httpx.Client") as client_cls:
        client_cls.return_value.__enter__.return_value = mock_fail
        second = api_client.post("/api/v1/leads/", {"company_name": "Contoso", "website": "https://contoso.test"}, format="json", **headers)
    assert second.status_code == 201
    assert second.data["crm_synced"] is False
    connection.refresh_from_db()
    assert connection.last_error


@pytest.mark.django_db
def test_lead_and_audit_push_to_google_sheets(tenant):
    from apps.audits.models import Audit
    from apps.integrations.push import push_audit, push_lead
    from apps.leads.models import Lead
    from apps.websites.models import Website

    _enable_integrations(tenant)
    CRMConnection.objects.create(
        tenant=tenant,
        provider="google_sheets",
        status=CRMConnection.Status.CONNECTED,
        enabled=True,
        config={
            "spreadsheet_id": "1AbCdEfGhIjKlMnOpQrStUvWxYz1234567890",
            "client_email": "seonet-sheets@demo.iam.gserviceaccount.com",
            "push_leads": True,
            "push_results": True,
        },
        encrypted_config={"private_key": "-----BEGIN PRIVATE KEY-----\nMIIE\n-----END PRIVATE KEY-----\n"},
    )
    lead = Lead.objects.create(tenant=tenant, company_name="Globex", website="https://globex.test", source_record_id="globex")
    website = Website.objects.create(tenant=tenant, url="https://globex.test", domain="globex.test", name="Globex")
    audit = Audit.objects.create(
        tenant=tenant,
        website=website,
        status=Audit.Status.COMPLETED,
        overall_score=72,
        scores={"technical_seo": 80, "on_page_seo": 70, "aeo": 60, "geo": 50},
        pages_crawled=12,
        issue_count=3,
    )
    with patch("apps.integrations.push.append_sheet_row") as append:
        push_lead(tenant, lead, event="lead.created")
        push_audit(tenant, audit)
    assert append.call_count == 2
    lead.refresh_from_db()
    assert lead.crm_synced is True
    connection = CRMConnection.objects.get(tenant=tenant, provider="google_sheets")
    assert connection.records_synced == 2
