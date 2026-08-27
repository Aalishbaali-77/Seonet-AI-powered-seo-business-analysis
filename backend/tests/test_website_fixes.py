from __future__ import annotations

from unittest.mock import patch

import pytest

from apps.audits.analysis import analyze_crawl
from apps.audits.models import Audit, Crawl, CrawlPage
from apps.common.crypto import decrypt_json, encrypt_json
from apps.crawler.parser import parse_html
from apps.websites.compare import intelligence_compare
from apps.websites.fixes import apply_planned_fixes, plan_fixes
from apps.websites.models import Website, WebsiteAccess
from apps.websites.transports import MemoryTransport


THIN = """
<html>
<head></head>
<body><p>Hi</p></body>
</html>
"""


def _audit(tenant, html=THIN):
    website = Website.objects.create(
        tenant=tenant,
        url="https://acme.test",
        domain="acme.test",
        name="Acme",
        business_name="Acme",
        description="Industrial pumps for factories.",
        target_markets=["Karachi"],
    )
    crawl = Crawl.objects.create(
        tenant=tenant,
        website=website,
        status=Crawl.Status.COMPLETED,
        signals={"https": True, "robots_txt": {"found": False}, "sitemap": {"found": False}},
    )
    extracted = parse_html("https://acme.test/", html)
    CrawlPage.objects.create(tenant=tenant, crawl=crawl, url="https://acme.test/", status_code=200, title=extracted.get("title") or "", extracted=extracted)
    audit = Audit.objects.create(tenant=tenant, website=website, crawl=crawl, status=Audit.Status.RUNNING)
    analyze_crawl(audit, crawl)
    audit.refresh_from_db()
    return website, audit


@pytest.mark.django_db
def test_plan_and_apply_keep_baseline_and_compare(tenant):
    website, audit = _audit(tenant)
    baseline_id = audit.id
    baseline_issues = audit.issue_count
    plan = plan_fixes(website=website, audit=audit, can_write_files=True, wordpress=False)
    assert any(item["code"] == "robots_txt" for item in plan["applicable"])
    transport = MemoryTransport({"index.html": THIN.encode()})
    applied = apply_planned_fixes(website=website, audit=audit, transport=transport, plan=plan)
    assert applied["applied"]
    assert "robots.txt" in transport.files
    assert "sitemap.xml" in transport.files
    assert b"application/ld+json" in transport.files["index.html"]
    audit.refresh_from_db()
    assert audit.id == baseline_id
    assert audit.issue_count == baseline_issues
    follow = Audit.objects.create(tenant=tenant, website=website, status=Audit.Status.COMPLETED, overall_score=70, scores={"aeo": 40, "geo": 30}, issue_count=2)
    audit.overall_score = 40
    audit.scores = {"aeo": 10, "geo": 10}
    audit.save(update_fields=["overall_score", "scores"])
    compared = intelligence_compare(baseline=audit, followup=follow)
    assert compared["available"] is True
    assert compared["origin"] == "audit_scores"
    assert "not a Google ranking" in compared["why"]
    assert compared["baseline_audit_id"] == str(audit.id)
    assert compared["followup_audit_id"] == str(follow.id)
    overall = next(row for row in compared["rows"] if row["metric"] == "Overall audit score")
    assert overall["delta"] == 30


@pytest.mark.django_db
def test_wordpress_cannot_write_files_without_ftp(tenant):
    website, audit = _audit(tenant)
    plan = plan_fixes(website=website, audit=audit, can_write_files=False, wordpress=True)
    assert any("FTP" in item["reason"] or "file" in item["reason"].lower() for item in plan["skipped"])


@pytest.mark.django_db
def test_apply_fixes_api_uses_connected_access_and_isolates_tenants(api_client, user, tenant, other_user, other_tenant, monkeypatch):
    website, audit = _audit(tenant)
    WebsiteAccess.objects.create(
        tenant=tenant,
        website=website,
        kind=WebsiteAccess.Kind.FTP,
        status=WebsiteAccess.Status.CONNECTED,
        config={"host": "ftp.example.com", "username": "acme"},
        secret_blob=encrypt_json({"username": "acme", "password": "secret"}),
    )
    store = MemoryTransport({"index.html": THIN.encode()})
    store.kind = "ftp"
    store.test = lambda: "ok"
    monkeypatch.setattr("apps.websites.fix_jobs.access_transport", lambda access: store)
    monkeypatch.setattr(
        "apps.websites.fix_jobs.execute_audit_job",
        lambda job: _complete_followup(job, website, tenant),
    )
    api_client.force_authenticate(user=user)
    headers = {"HTTP_X_TENANT_ID": str(tenant.id)}
    planned = api_client.get(f"/api/v1/websites/{website.id}/fix-plan/?audit={audit.id}", **headers)
    assert planned.status_code == 200
    assert planned.data["applicable"]
    started = api_client.post(f"/api/v1/websites/{website.id}/apply-fixes/", {"audit_id": str(audit.id)}, format="json", **headers)
    assert started.status_code == 202
    assert started.data["job_type"] == "apply_audit_fixes"
    assert started.data["status"] == "COMPLETED"
    assert started.data["result"]["baseline_audit_id"] == str(audit.id)
    assert started.data["result"]["followup_audit_id"]
    assert started.data["result"]["followup_audit_id"] != str(audit.id)
    runs = api_client.get(f"/api/v1/websites/{website.id}/fix-runs/", **headers)
    assert runs.status_code == 200
    assert runs.data["results"][0]["comparison"]["available"] is True
    secrets = decrypt_json(WebsiteAccess.objects.get(website=website).secret_blob)
    assert secrets["password"] == "secret"
    api_client.force_authenticate(user=other_user)
    other = api_client.get(f"/api/v1/websites/{website.id}/fix-runs/", HTTP_X_TENANT_ID=str(other_tenant.id))
    assert other.status_code == 404


def _complete_followup(job, website, tenant):
    from apps.audits.models import Audit
    from apps.jobs import services as job_services

    follow = Audit.objects.filter(job=job).first()
    follow.status = Audit.Status.COMPLETED
    follow.overall_score = 66
    follow.scores = {"aeo": 22, "geo": 18, "technical_seo": 40}
    follow.issue_count = 3
    follow.save()
    job_services.mark_completed(job, result={"stage": "Completed", "audit_id": str(follow.id)})
    return follow
