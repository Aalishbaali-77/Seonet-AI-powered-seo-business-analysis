from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.auditlog.models import AuditLog
from apps.crm.models import Activity, Company, Deal
from apps.crm.services import ensure_default_pipeline
from apps.leads.models import Lead


def _headers(tenant):
    return {"HTTP_X_TENANT_ID": str(tenant.id)}


@pytest.mark.django_db
def test_deal_rejects_foreign_stage_and_company(api_client, user, tenant, other_user, other_tenant):
    ensure_default_pipeline(tenant)
    ensure_default_pipeline(other_tenant)
    api_client.force_authenticate(user=other_user)
    foreign_pipeline = api_client.get("/api/v1/crm/pipelines/", HTTP_X_TENANT_ID=str(other_tenant.id))
    foreign = api_client.post(
        "/api/v1/crm/companies/",
        {"name": "Beta Co"},
        format="json",
        HTTP_X_TENANT_ID=str(other_tenant.id),
    )
    assert foreign.status_code == 201
    api_client.force_authenticate(user=user)
    headers = _headers(tenant)
    home = api_client.get("/api/v1/crm/pipelines/", **headers).data[0]
    company = api_client.post("/api/v1/crm/companies/", {"name": "Acme Co"}, format="json", **headers)
    assert company.status_code == 201
    rejected = api_client.post(
        "/api/v1/crm/deals/",
        {
            "pipeline": home["id"],
            "stage": home["stages"][1]["id"],
            "company": foreign.data["id"],
            "name": "Cross tenant",
            "amount": "10",
        },
        format="json",
        **headers,
    )
    assert rejected.status_code == 400
    wrong_stage = api_client.post(
        "/api/v1/crm/deals/",
        {
            "pipeline": home["id"],
            "stage": foreign_pipeline.data[0]["stages"][0]["id"],
            "company": company.data["id"],
            "name": "Wrong stage",
        },
        format="json",
        **headers,
    )
    assert wrong_stage.status_code == 400
    created = api_client.post(
        "/api/v1/crm/deals/",
        {
            "pipeline": home["id"],
            "stage": home["stages"][0]["id"],
            "company": company.data["id"],
            "name": "Pilot",
            "amount": "2500",
            "currency": "PKR",
        },
        format="json",
        **headers,
    )
    assert created.status_code == 201
    assert str(created.data["owner"]) == str(user.id)
    api_client.force_authenticate(user=other_user)
    hidden = api_client.get(f"/api/v1/crm/deals/{created.data['id']}/", HTTP_X_TENANT_ID=str(other_tenant.id))
    assert hidden.status_code == 404


@pytest.mark.django_db
def test_deal_delete_and_funnel_has_no_forecast(api_client, user, tenant):
    ensure_default_pipeline(tenant)
    api_client.force_authenticate(user=user)
    headers = _headers(tenant)
    pipeline = api_client.get("/api/v1/crm/pipelines/", **headers).data[0]
    company = api_client.post("/api/v1/crm/companies/", {"name": "Buyer Co"}, format="json", **headers)
    deal = api_client.post(
        "/api/v1/crm/deals/",
        {
            "pipeline": pipeline["id"],
            "stage": pipeline["stages"][0]["id"],
            "company": company.data["id"],
            "name": "Pilot",
            "amount": "1200",
        },
        format="json",
        **headers,
    )
    assert deal.status_code == 201
    funnel = api_client.get("/api/v1/crm/funnel/", **headers)
    assert funnel.status_code == 200
    assert funnel.data["origin"] == "fact"
    assert "win-rate" in funnel.data["why"].lower()
    assert "win_rate" not in funnel.data
    assert all("win_rate" not in row for row in funnel.data["stages"])
    assert sum(row["deals"] for row in funnel.data["stages"]) == 1
    assert any(row["amount"] == "1200.00" or row["amount"] == "1200" for row in funnel.data["stages"])
    removed = api_client.delete(f"/api/v1/crm/deals/{deal.data['id']}/", **headers)
    assert removed.status_code == 204
    assert Deal.objects.for_tenant(tenant).count() == 0
    missing = api_client.get(f"/api/v1/crm/deals/{deal.data['id']}/", **headers)
    assert missing.status_code == 404
    empty = api_client.get("/api/v1/crm/funnel/", **headers)
    assert sum(row["deals"] for row in empty.data["stages"]) == 0
    assert AuditLog.objects.filter(tenant=tenant, action="CRM_DEAL_DELETED").exists()


@pytest.mark.django_db
def test_deal_won_stores_closed_at_and_company_tags(api_client, user, tenant):
    ensure_default_pipeline(tenant)
    api_client.force_authenticate(user=user)
    headers = _headers(tenant)
    pipeline = api_client.get("/api/v1/crm/pipelines/", **headers).data[0]
    won = next(item for item in pipeline["stages"] if item["is_won"])
    company = api_client.post(
        "/api/v1/crm/companies/",
        {"name": "Tag Co", "phone": "03001234567", "tags": ["packaging", "karachi"], "notes": "Buyer"},
        format="json",
        **headers,
    )
    assert company.status_code == 201
    assert company.data["tags"] == ["packaging", "karachi"]
    deal = api_client.post(
        "/api/v1/crm/deals/",
        {
            "pipeline": pipeline["id"],
            "stage": pipeline["stages"][0]["id"],
            "company": company.data["id"],
            "name": "Close me",
            "amount": "500",
            "priority": "high",
        },
        format="json",
        **headers,
    )
    moved = api_client.patch(
        f"/api/v1/crm/deals/{deal.data['id']}/",
        {"stage": won["id"], "won_reason": "Signed annual"},
        format="json",
        **headers,
    )
    assert moved.status_code == 200
    assert moved.data["closed_at"]
    assert moved.data["won_reason"] == "Signed annual"
    assert moved.data["priority"] == "high"
    reports = api_client.get("/api/v1/reports/", **headers)
    crm_row = next(item for item in reports.data["results"] if item["code"] == "crm")
    assert crm_row["count"] == 1
    assert any(row["deals"] == 1 for row in crm_row["stages"])
    filtered = api_client.get("/api/v1/crm/deals/?priority=high", **headers)
    assert filtered.data["count"] == 1


@pytest.mark.django_db
def test_promote_and_relink_marks_crm_synced(api_client, user, tenant):
    ensure_default_pipeline(tenant)
    api_client.force_authenticate(user=user)
    headers = _headers(tenant)
    lead = Lead.objects.create(tenant=tenant, company_name="Pack Co", email="buyer@pack.test", source="manual")
    pipeline = api_client.get("/api/v1/crm/pipelines/", **headers).data[0]
    company = api_client.post("/api/v1/crm/companies/", {"name": "Pack Co"}, format="json", **headers)
    contact = api_client.post(
        "/api/v1/crm/contacts/",
        {"company": company.data["id"], "first_name": "Buyer", "email": "buyer@pack.test", "title": "Owner"},
        format="json",
        **headers,
    )
    assert contact.status_code == 201
    deal = api_client.post(
        "/api/v1/crm/deals/",
        {
            "pipeline": pipeline["id"],
            "stage": pipeline["stages"][0]["id"],
            "company": company.data["id"],
            "contact": contact.data["id"],
            "name": "Pack Co",
            "amount": "0",
            "lead": str(lead.id),
        },
        format="json",
        **headers,
    )
    assert deal.status_code == 201
    lead.refresh_from_db()
    assert lead.crm_synced is True
    promoted = api_client.get("/api/v1/crm/deals/?has_lead=true", **headers)
    assert promoted.data["count"] == 1
    Lead.objects.filter(id=lead.id).update(crm_synced=False)
    linked = api_client.patch(f"/api/v1/crm/deals/{deal.data['id']}/", {"lead": str(lead.id)}, format="json", **headers)
    assert linked.status_code == 200
    lead.refresh_from_db()
    assert lead.crm_synced is True


@pytest.mark.django_db
def test_activity_overdue_and_complete_filters(api_client, user, tenant):
    ensure_default_pipeline(tenant)
    api_client.force_authenticate(user=user)
    headers = _headers(tenant)
    company = api_client.post("/api/v1/crm/companies/", {"name": "Follow Co"}, format="json", **headers)
    past = api_client.post(
        "/api/v1/crm/activities/",
        {
            "company": company.data["id"],
            "kind": "task",
            "title": "Call back",
            "due_at": (timezone.now() - timedelta(days=1)).isoformat(),
        },
        format="json",
        **headers,
    )
    assert past.status_code == 201
    overdue = api_client.get("/api/v1/crm/activities/?overdue=true", **headers)
    assert overdue.status_code == 200
    assert overdue.data["count"] == 1
    done = api_client.patch(
        f"/api/v1/crm/activities/{past.data['id']}/",
        {"completed_at": timezone.now().isoformat()},
        format="json",
        **headers,
    )
    assert done.status_code == 200
    assert done.data["completed_at"]
    empty = api_client.get("/api/v1/crm/activities/?overdue=true", **headers)
    assert empty.data["count"] == 0
    completed = api_client.get("/api/v1/crm/activities/?completed=true", **headers)
    assert completed.data["count"] == 1


@pytest.mark.django_db
def test_assignees_and_company_industry_filter(api_client, user, tenant, viewer):
    api_client.force_authenticate(user=user)
    headers = _headers(tenant)
    api_client.post("/api/v1/crm/companies/", {"name": "Tea Co", "industry": "packaging"}, format="json", **headers)
    api_client.post("/api/v1/crm/companies/", {"name": "Rice Co", "industry": "food"}, format="json", **headers)
    packaging = api_client.get("/api/v1/crm/companies/?industry=packaging", **headers)
    assert packaging.data["count"] == 1
    assignees = api_client.get("/api/v1/crm/assignees/", **headers)
    assert assignees.status_code == 200
    ids = {row["id"] for row in assignees.data}
    assert str(user.id) in ids
    assert str(viewer.id) in ids
    assert Company.objects.for_tenant(tenant).count() == 2
    assert Activity.objects.for_tenant(tenant).count() == 0


@pytest.mark.django_db
def test_pipeline_stage_editor_and_export(api_client, user, tenant):
    ensure_default_pipeline(tenant)
    api_client.force_authenticate(user=user)
    headers = _headers(tenant)
    created = api_client.post("/api/v1/crm/pipelines/", {"name": "Enterprise"}, format="json", **headers)
    assert created.status_code == 201
    assert created.data["is_default"] is False
    assert len(created.data["stages"]) >= 2
    stage = api_client.post(
        f"/api/v1/crm/pipelines/{created.data['id']}/stages/",
        {"name": "Legal review", "code": "legal", "order": 20},
        format="json",
        **headers,
    )
    assert stage.status_code == 201
    exported = api_client.get("/api/v1/crm/export/?kind=companies", **headers)
    assert exported.status_code == 200
    assert "text/csv" in exported["Content-Type"]
    assert b"name" in exported.content
