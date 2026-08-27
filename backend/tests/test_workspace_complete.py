from __future__ import annotations

import pytest

from apps.crm.models import Activity, Company, Deal
from apps.crm.services import ensure_default_pipeline
from apps.leads.models import Lead, LeadList
from apps.leads.scoring import apply_lead_score, score_lead
from apps.opportunities.models import Opportunity
from apps.usage.models import UsageRecord


@pytest.mark.django_db
def test_lead_score_uses_completeness_and_does_not_invent_contact(tenant):
    lead = Lead.objects.create(tenant=tenant, company_name="Acme", source="manual", source_record_id="acme")
    payload = score_lead(lead)
    assert payload["quality_score"] == 0
    assert "email" in payload["missing_fields"]
    assert payload["origin"] == "fact"
    lead.website = "https://acme.example"
    lead.location = "Karachi"
    payload = score_lead(lead)
    assert payload["quality_score"] == 40
    assert payload["lead_score"] == 40


@pytest.mark.django_db
def test_crm_company_contact_activity_and_stage_move(api_client, user, tenant):
    ensure_default_pipeline(tenant)
    api_client.force_authenticate(user=user)
    headers = {"HTTP_X_TENANT_ID": str(tenant.id)}
    company = api_client.post("/api/v1/crm/companies/", {"name": "Buyer Co", "location": "Lahore"}, format="json", **headers)
    assert company.status_code == 201
    contact = api_client.post(
        "/api/v1/crm/contacts/",
        {"company": company.data["id"], "first_name": "Sara", "email": "sara@example.com"},
        format="json",
        **headers,
    )
    assert contact.status_code == 201
    pipelines = api_client.get("/api/v1/crm/pipelines/", **headers)
    pipeline = pipelines.data[0]
    stage = pipeline["stages"][0]
    next_stage = pipeline["stages"][1]
    deal = api_client.post(
        "/api/v1/crm/deals/",
        {"pipeline": pipeline["id"], "stage": stage["id"], "company": company.data["id"], "name": "Pilot", "amount": "0"},
        format="json",
        **headers,
    )
    assert deal.status_code == 201
    moved = api_client.patch(f"/api/v1/crm/deals/{deal.data['id']}/", {"stage": next_stage["id"]}, format="json", **headers)
    assert moved.status_code == 200
    assert str(moved.data["stage"]) == str(next_stage["id"])
    note = api_client.post(
        "/api/v1/crm/activities/",
        {"company": company.data["id"], "deal": deal.data["id"], "kind": "note", "title": "Intro call"},
        format="json",
        **headers,
    )
    assert note.status_code == 201
    assert Company.objects.for_tenant(tenant).count() == 1
    assert Deal.objects.for_tenant(tenant).count() == 1
    assert Activity.objects.for_tenant(tenant).count() == 1
    funnel = api_client.get("/api/v1/crm/funnel/", **headers)
    assert funnel.status_code == 200
    assert funnel.data["origin"] == "fact"
    assert sum(row["deals"] for row in funnel.data["stages"]) == 1


@pytest.mark.django_db
def test_lead_list_members_and_promote_marks_crm_synced(api_client, user, tenant):
    ensure_default_pipeline(tenant)
    api_client.force_authenticate(user=user)
    headers = {"HTTP_X_TENANT_ID": str(tenant.id)}
    lead = api_client.post("/api/v1/leads/", {"company_name": "Pack Co", "location": "Karachi"}, format="json", **headers)
    assert lead.status_code == 201
    saved = LeadList.objects.create(tenant=tenant, name="Karachi packaging")
    added = api_client.post(
        f"/api/v1/leads/lists/{saved.id}/members/",
        {"lead_ids": [lead.data["id"]]},
        format="json",
        **headers,
    )
    assert added.status_code == 200
    detail = api_client.get(f"/api/v1/leads/lists/{saved.id}/", **headers)
    assert detail.status_code == 200
    assert detail.data["lead_count"] == 1
    pipelines = api_client.get("/api/v1/crm/pipelines/", **headers)
    pipeline = pipelines.data[0]
    company = api_client.post("/api/v1/crm/companies/", {"name": "Pack Co"}, format="json", **headers)
    deal = api_client.post(
        "/api/v1/crm/deals/",
        {
            "pipeline": pipeline["id"],
            "stage": pipeline["stages"][0]["id"],
            "company": company.data["id"],
            "name": "Pack Co",
            "lead": lead.data["id"],
        },
        format="json",
        **headers,
    )
    assert deal.status_code == 201
    refreshed = api_client.get(f"/api/v1/leads/{lead.data['id']}/", **headers)
    assert refreshed.data["crm_synced"] is True
    scored = api_client.post("/api/v1/leads/score/", {}, format="json", **headers)
    assert scored.status_code == 200
    assert scored.data["scored"] >= 1


@pytest.mark.django_db
def test_advisor_and_opportunity_generate_stay_factual(api_client, user, tenant):
    api_client.force_authenticate(user=user)
    headers = {"HTTP_X_TENANT_ID": str(tenant.id)}
    advice = api_client.post("/api/v1/ai/advisor/", {"domain": "business"}, format="json", **headers)
    assert advice.status_code == 200
    assert advice.data["facts"]
    assert "invent" not in (advice.data.get("inference") or "").lower()
    generated = api_client.post("/api/v1/opportunities/generate/", {}, format="json", **headers)
    assert generated.status_code == 200
    assert generated.data["created"] == 0
    assert Opportunity.objects.for_tenant(tenant).count() == 0


@pytest.mark.django_db
def test_dashboard_lead_intelligence_uses_stored_fields(api_client, user, tenant):
    lead = Lead.objects.create(
        tenant=tenant,
        company_name="Pack Co",
        industry="Packaging",
        location="Karachi",
        website="https://pack.example",
        source="manual",
        source_record_id="pack-intel",
    )
    apply_lead_score(lead)
    api_client.force_authenticate(user=user)
    response = api_client.get("/api/v1/dashboard/overview/", HTTP_X_TENANT_ID=str(tenant.id))
    assert response.status_code == 200
    intel = response.data["lead_intelligence"]
    assert intel["data_quality"]["leads"] == 1
    assert intel["data_quality"]["with_website"] == 1
    assert intel["data_quality"]["with_email"] == 0
    assert intel["by_industry"] == [{"industry": "Packaging", "count": 1}]
    assert intel["by_location"] == [{"location": "Karachi", "count": 1}]
    assert intel["score_distribution"]
    assert len(intel["new_leads_over_time"]) == 14
    assert sum(row["count"] for row in intel["new_leads_over_time"]) == 1


@pytest.mark.django_db
def test_lead_export_csv_is_stored_fields_only(api_client, user, tenant, viewer):
    Lead.objects.create(
        tenant=tenant,
        company_name="Export Co",
        email="ops@export.example",
        location="Lahore",
        source="manual",
        source_record_id="export-co",
        status=Lead.Status.QUALIFIED,
    )
    api_client.force_authenticate(user=user)
    headers = {"HTTP_X_TENANT_ID": str(tenant.id)}
    response = api_client.get("/api/v1/leads/export/?status=qualified", **headers)
    assert response.status_code == 200
    assert "text/csv" in response["Content-Type"]
    body = response.content.decode("utf-8")
    assert "Export Co" in body
    assert "ops@export.example" in body
    assert "Lahore" in body
    assert UsageRecord.objects.for_tenant(tenant).filter(event_type="lead_exported").exists()
    api_client.force_authenticate(user=viewer)
    denied = api_client.get("/api/v1/leads/export/", **headers)
    assert denied.status_code == 403


@pytest.mark.django_db
def test_opportunity_related_leads_are_existing_workspace_leads(api_client, user, tenant):
    api_client.force_authenticate(user=user)
    headers = {"HTTP_X_TENANT_ID": str(tenant.id)}
    lead = Lead.objects.create(tenant=tenant, company_name="Linked Co", location="Islamabad", source="manual", source_record_id="linked-co")
    created = api_client.post(
        "/api/v1/opportunities/",
        {
            "title": "Islamabad packaging",
            "type": "geographic",
            "evidence": "Imported orders name Islamabad as a city.",
            "recommended_action": "Link existing leads in that city.",
        },
        format="json",
        **headers,
    )
    assert created.status_code == 201
    patched = api_client.patch(
        f"/api/v1/opportunities/{created.data['id']}/",
        {"related_lead_ids": [str(lead.id)]},
        format="json",
        **headers,
    )
    assert patched.status_code == 200
    assert patched.data["related_leads"][0]["company_name"] == "Linked Co"
    preview = api_client.get(
        f"/api/v1/marketing/audiences/preview/?audience_type=opportunity&opportunity={created.data['id']}",
        **headers,
    )
    assert preview.status_code == 200
    assert preview.data["count"] == 1
