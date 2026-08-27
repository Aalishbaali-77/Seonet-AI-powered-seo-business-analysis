from __future__ import annotations

import pytest

from apps.leads.enrichment import enrich_lead
from apps.leads.models import Lead


@pytest.mark.django_db
def test_enrich_does_not_invent_contact_fields(api_client, user, tenant):
    lead = Lead.objects.create(tenant=tenant, company_name="Empty Co", source="manual", source_record_id="empty-co")
    api_client.force_authenticate(user=user)
    response = api_client.post(f"/api/v1/leads/{lead.id}/enrich/", {}, HTTP_X_TENANT_ID=str(tenant.id))
    assert response.status_code == 200
    assert response.data["filled"] == []
    assert "email" in response.data["missing_fields"]
    assert "phone" in response.data["missing_fields"]
    lead.refresh_from_db()
    assert lead.email == ""
    assert lead.phone == ""
    assert "invent" in response.data["why"].lower() or "empty" in response.data["why"].lower()


@pytest.mark.django_db
def test_enrich_writes_contacts_from_company_website(tenant, monkeypatch):
    lead = Lead.objects.create(
        tenant=tenant,
        company_name="Site Co",
        website="https://siteco.test",
        source="manual",
        source_record_id="site-co",
    )

    def fake_site(_url: str) -> dict[str, str]:
        return {"email": "hello@siteco.test", "phone": "+92 300 1234567", "description": "Packaging", "linkedin_url": ""}

    monkeypatch.setattr("apps.leads.enrichment.read_company_website", fake_site)
    result = enrich_lead(lead)
    fields = {item["field"] for item in result["filled"]}
    assert "email" in fields
    assert "phone" in fields
    lead.refresh_from_db()
    assert lead.email == "hello@siteco.test"
    assert lead.phone == "+92 300 1234567"
    assert "email" not in result["missing_fields"]


@pytest.mark.django_db
def test_enrich_uses_hunter_when_enabled(tenant, monkeypatch):
    from apps.platform.lead_sources import ensure_lead_sources
    from apps.platform.models import LeadSource

    ensure_lead_sources()
    source = LeadSource.objects.get(code="hunter")
    source.is_enabled = True
    source.encrypted_config = {"api_key": "hunter-test"}
    source.save()
    lead = Lead.objects.create(
        tenant=tenant,
        company_name="Hunt Co",
        website="https://huntco.test",
        source="manual",
        source_record_id="hunt-co",
    )
    monkeypatch.setattr("apps.leads.enrichment.read_company_website", lambda _url: {})
    monkeypatch.setattr(
        "providers.leads.enrichment.HunterAdapter.lookup",
        lambda self, **kwargs: {"email": "sales@huntco.test"},
    )
    result = enrich_lead(lead)
    lead.refresh_from_db()
    assert lead.email == "sales@huntco.test"
    assert any(item["source"] == "hunter" for item in result["filled"])


@pytest.mark.django_db
def test_bulk_enrich_starts_job(api_client, user, tenant):
    Lead.objects.create(tenant=tenant, company_name="Bulk Co", source="manual", source_record_id="bulk-co")
    api_client.force_authenticate(user=user)
    response = api_client.post("/api/v1/leads/enrich/", {}, format="json", HTTP_X_TENANT_ID=str(tenant.id))
    assert response.status_code == 202
    assert response.data["job"]["job_type"] == "enrich_leads"
