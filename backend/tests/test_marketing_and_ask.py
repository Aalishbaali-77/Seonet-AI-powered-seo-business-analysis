from __future__ import annotations

import pytest

from apps.business.models import CommerceCustomer
from apps.leads.models import Lead, LeadList
from apps.marketing.models import Campaign
from apps.notifications.models import Notification


@pytest.mark.django_db
def test_campaign_audience_is_list_count_and_send_does_not_invent(api_client, user, tenant):
    api_client.force_authenticate(user=user)
    headers = {"HTTP_X_TENANT_ID": str(tenant.id)}
    saved = LeadList.objects.create(tenant=tenant, name="Karachi list")
    lead = Lead.objects.create(tenant=tenant, company_name="Pack Co", source="manual", source_record_id="pack-co")
    saved.leads.add(lead)
    created = api_client.post(
        "/api/v1/marketing/campaigns/",
        {"name": "Ramadan offer", "audience_type": "lead_list", "lead_list": str(saved.id), "channel": "offer"},
        format="json",
        **headers,
    )
    assert created.status_code == 201
    assert created.data["live_audience_count"] == 1
    sent = api_client.post(f"/api/v1/marketing/campaigns/{created.data['id']}/send/", {}, format="json", **headers)
    assert sent.status_code == 200
    assert sent.data["status"] == "sent"
    assert sent.data["audience_count"] == 1
    assert "email" in sent.data["send_note"].lower()
    assert Campaign.objects.for_tenant(tenant).count() == 1
    assert Notification.objects.for_tenant(tenant).filter(user=user, title__startswith="Campaign recorded").exists()
    exported = api_client.get(f"/api/v1/marketing/audiences/export/?audience_type=lead_list&lead_list={saved.id}", **headers)
    assert exported.status_code == 200
    assert b"Pack Co" in exported.content
    read_all = api_client.post("/api/v1/notifications/read-all/", {}, format="json", **headers)
    assert read_all.status_code == 200
    assert read_all.data["updated"] >= 1


@pytest.mark.django_db
def test_campaign_commerce_city_counts_imported_customers(api_client, user, tenant):
    CommerceCustomer.objects.create(tenant=tenant, name="Buyer", city="Lahore")
    CommerceCustomer.objects.create(tenant=tenant, name="Other", city="Karachi")
    api_client.force_authenticate(user=user)
    headers = {"HTTP_X_TENANT_ID": str(tenant.id)}
    created = api_client.post(
        "/api/v1/marketing/campaigns/",
        {"name": "Lahore buyers", "audience_type": "commerce_city", "city": "Lahore", "channel": "offer"},
        format="json",
        **headers,
    )
    assert created.status_code == 201
    assert created.data["live_audience_count"] == 1
    preview = api_client.get("/api/v1/marketing/audiences/preview/?audience_type=commerce_city&city=Lahore", **headers)
    assert preview.data["count"] == 1
    overview = api_client.get("/api/v1/business/overview/", **headers)
    assert "Lahore" in overview.data["kpis"]["customer_cities"]


@pytest.mark.django_db
def test_ask_maps_to_workspace_counts(api_client, user, tenant):
    Lead.objects.create(tenant=tenant, company_name="One", source="manual", source_record_id="one")
    api_client.force_authenticate(user=user)
    answer = api_client.post(
        "/api/v1/ai/query/",
        {"question": "How many leads are in this workspace?"},
        format="json",
        HTTP_X_TENANT_ID=str(tenant.id),
    )
    assert answer.status_code == 200
    assert answer.data["intent"] == "count_leads"
    assert "1 leads" in answer.data["facts"][0]
    blocked = api_client.post(
        "/api/v1/ai/query/",
        {"question": "What will revenue be next year in Lahore?"},
        format="json",
        HTTP_X_TENANT_ID=str(tenant.id),
    )
    assert blocked.status_code == 200
    assert blocked.data["intent"] is None
    assert blocked.data["facts"] == []
    market = api_client.post(
        "/api/v1/ai/query/",
        {"question": "Where should we expand for this business?"},
        format="json",
        HTTP_X_TENANT_ID=str(tenant.id),
    )
    assert market.status_code == 200
    assert market.data["intent"] == "market_analysis"
    assert market.data["facts"]
    assert market.data["job_id"]


@pytest.mark.django_db
def test_reports_catalog_lists_empty_modules_honestly(api_client, user, tenant):
    api_client.force_authenticate(user=user)
    response = api_client.get("/api/v1/reports/", HTTP_X_TENANT_ID=str(tenant.id))
    assert response.status_code == 200
    codes = {item["code"] for item in response.data["results"]}
    assert {"audits", "business", "markets", "opportunities", "marketing", "leads", "crm"} <= codes
    business = next(item for item in response.data["results"] if item["code"] == "business")
    assert business["available"] is False
    exported = api_client.get("/api/v1/reports/export/", HTTP_X_TENANT_ID=str(tenant.id))
    assert exported.status_code == 200
    assert exported.data["origin"] == "fact"
