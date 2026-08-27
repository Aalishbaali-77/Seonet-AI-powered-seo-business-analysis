from __future__ import annotations

import uuid

import pytest
from rest_framework.test import APIClient

from apps.jobs.models import Job


@pytest.mark.django_db
def test_tenant_cannot_read_other_tenant_job(api_client, user, tenant, other_tenant):
    job = Job.objects.create(tenant=other_tenant, job_type="crawl_website", status=Job.Status.QUEUED)
    api_client.force_authenticate(user=user)
    response = api_client.get(f"/api/v1/jobs/{job.id}/", HTTP_X_TENANT_ID=str(tenant.id))
    assert response.status_code == 404
    assert response.data["error"]["code"] == "NOT_FOUND"


@pytest.mark.django_db
def test_tenant_can_list_and_cancel_own_job(api_client, user, tenant):
    job = Job.objects.create(tenant=tenant, user=user, job_type="enrich_leads", status=Job.Status.QUEUED)
    api_client.force_authenticate(user=user)
    listed = api_client.get("/api/v1/jobs/", HTTP_X_TENANT_ID=str(tenant.id))
    assert listed.status_code == 200
    assert listed.data["count"] == 1
    cancelled = api_client.post(f"/api/v1/jobs/{job.id}/cancel/", {}, format="json", HTTP_X_TENANT_ID=str(tenant.id))
    assert cancelled.status_code == 200
    assert cancelled.data["status"] == Job.Status.CANCELLED


@pytest.mark.django_db
def test_invalid_uuid_does_not_bypass(api_client, user, tenant):
    api_client.force_authenticate(user=user)
    response = api_client.get(f"/api/v1/jobs/{uuid.uuid4()}/", HTTP_X_TENANT_ID=str(tenant.id))
    assert response.status_code == 404


@pytest.mark.django_db
def test_viewer_cannot_manage_settings(viewer, tenant):
    client = APIClient()
    client.force_authenticate(user=viewer)
    response = client.patch(
        f"/api/v1/tenants/{tenant.id}/",
        {"name": "Hacked"},
        format="json",
        HTTP_X_TENANT_ID=str(tenant.id),
    )
    assert response.status_code == 403
    assert response.data["error"]["code"] == "PERMISSION_DENIED"


@pytest.mark.django_db
def test_header_cannot_select_foreign_tenant(api_client, user, tenant, other_tenant):
    api_client.force_authenticate(user=user)
    response = api_client.get("/api/v1/dashboard/overview/", HTTP_X_TENANT_ID=str(other_tenant.id))
    # Middleware ignores unauthorized tenant ids and falls back to the user's tenant.
    assert response.status_code == 200
    me = api_client.get("/api/v1/auth/me/", HTTP_X_TENANT_ID=str(other_tenant.id))
    assert str(other_tenant.id) not in [item["id"] for item in me.data["tenants"]] or True
    tenant_ids = {str(item["id"]) for item in me.data["tenants"]}
    assert str(other_tenant.id) not in tenant_ids
    assert str(tenant.id) in tenant_ids


@pytest.mark.django_db
def test_tenant_dashboard_hides_platform_and_foreign_activity(api_client, user, tenant, other_tenant):
    from apps.auditlog.models import AuditLog
    from apps.auditlog.services import write_audit

    write_audit(action="WEBSITE_CREATED", tenant=tenant, user=user, resource_type="website")
    write_audit(action="PLATFORM_INVOICE_PAID", tenant=tenant, user=user, resource_type="invoice")
    write_audit(action="WEBSITE_CREATED", tenant=other_tenant, user=user, resource_type="website")

    api_client.force_authenticate(user=user)
    response = api_client.get("/api/v1/dashboard/overview/", HTTP_X_TENANT_ID=str(tenant.id))
    assert response.status_code == 200
    titles = [item["title"] for item in response.data["activity"]]
    assert "Website Created" in titles
    assert "Platform Invoice Paid" not in titles
    assert AuditLog.objects.filter(tenant=other_tenant, action="WEBSITE_CREATED").exists()
    assert all("Platform" not in title for title in titles)


@pytest.mark.django_db
def test_platform_overview_activity_excludes_workspace_events(db, tenant, user):
    from rest_framework.test import APIClient

    from apps.auditlog.services import write_audit
    from apps.users.models import User

    admin = User.objects.create_superuser(email="ops@example.com", password="SecurePass!123")
    write_audit(action="WEBSITE_CREATED", tenant=tenant, user=user, resource_type="website")
    write_audit(action="PLATFORM_PLAN_ASSIGNED", tenant=tenant, user=admin, resource_type="subscription")
    client = APIClient()
    client.force_authenticate(user=admin)
    response = client.get("/api/v1/platform/overview/")
    assert response.status_code == 200
    actions = [item["action"] for item in response.data["activity"]]
    assert "PLATFORM_PLAN_ASSIGNED" in actions
    assert "WEBSITE_CREATED" not in actions
