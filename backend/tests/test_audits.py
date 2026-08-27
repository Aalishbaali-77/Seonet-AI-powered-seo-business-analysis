from __future__ import annotations

from unittest.mock import patch

import pytest

from apps.audits.analysis import analyze_crawl
from apps.audits.models import Audit, AuditIssue, Crawl, CrawlPage
from apps.crawler.parser import parse_html
from apps.websites.models import Website


HTML = """
<html lang="en">
<head>
  <title>Acme industrial pumps for Karachi factories</title>
  <meta name="description" content="Acme sells industrial pumps and maintenance for factories across Karachi and the UAE with on-site support." />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta property="og:title" content="Acme pumps" />
  <link rel="canonical" href="https://acme.test/" />
  <link rel="icon" href="/favicon.ico" />
  <script type="application/ld+json">{"@type":"Organization","name":"Acme"}</script>
</head>
<body>
  <h1>Industrial pumps</h1>
  <h2>Karachi coverage</h2>
  <p>We install and service industrial pumps for factories. Call <a href="tel:+923001112233">+92 300 1112233</a>.</p>
  <address>12 Clifton, Karachi</address>
  <img src="/pump.jpg" alt="Pump" />
</body>
</html>
"""


def test_parse_html_extracts_schema_and_nap():
    extracted = parse_html("https://acme.test/", HTML)
    assert extracted["title"].startswith("Acme")
    assert extracted["json_ld"] is True
    assert "Organization" in extracted["json_ld_types"]
    assert extracted["html_lang"] == "en"
    assert extracted["has_viewport"] is True
    assert extracted["phones"]
    assert extracted["word_count"] > 10


@pytest.mark.django_db
def test_analyze_crawl_scores_are_computed_not_hardcoded(tenant):
    website = Website.objects.create(
        tenant=tenant,
        url="https://acme.test",
        domain="acme.test",
        name="Acme",
        keywords=["pumps"],
        target_markets=["Karachi"],
    )
    crawl = Crawl.objects.create(
        tenant=tenant,
        website=website,
        status=Crawl.Status.COMPLETED,
        signals={"https": True, "robots_txt": {"found": True}, "sitemap": {"found": True, "url_count": 4}},
    )
    extracted = parse_html("https://acme.test/", HTML)
    extracted.update({"elapsed_ms": 220, "size_bytes": 12000, "redirect_count": 0, "https": True, "content_encoding": "gzip"})
    CrawlPage.objects.create(
        tenant=tenant,
        crawl=crawl,
        url="https://acme.test/",
        status_code=200,
        title=extracted["title"],
        extracted=extracted,
    )
    audit = Audit.objects.create(tenant=tenant, website=website, crawl=crawl, status=Audit.Status.RUNNING)
    analyze_crawl(audit, crawl)
    audit.refresh_from_db()
    assert audit.status == Audit.Status.COMPLETED
    assert audit.overall_score and 40 <= audit.overall_score <= 100
    assert audit.scores["performance"] != 60
    assert "Organization" in (audit.summary.get("schema_types") or [])
    assert audit.summary.get("https") is True


@pytest.mark.django_db
def test_analyze_flags_missing_https_and_titles(tenant):
    website = Website.objects.create(tenant=tenant, url="http://thin.test", domain="thin.test", name="Thin")
    crawl = Crawl.objects.create(
        tenant=tenant,
        website=website,
        status=Crawl.Status.COMPLETED,
        signals={"https": False, "robots_txt": {"found": False}, "sitemap": {"found": False, "url_count": 0}},
    )
    CrawlPage.objects.create(
        tenant=tenant,
        crawl=crawl,
        url="http://thin.test/",
        status_code=200,
        title="",
        extracted={"title": "", "meta": {}, "canonical": "", "h1": [], "json_ld": False, "https": False, "word_count": 20, "images_missing_alt": 2},
    )
    audit = Audit.objects.create(tenant=tenant, website=website, crawl=crawl, status=Audit.Status.RUNNING)
    analyze_crawl(audit, crawl)
    titles = set(audit.issues.values_list("title", flat=True))
    assert "Missing title tags" in titles
    assert "Site is not fully served over HTTPS" in titles
    assert "No JSON-LD structured data detected" in titles
    assert audit.scores["technical_seo"] < 90
    assert audit.scores["aeo"] < 70


@pytest.mark.django_db
def test_issue_status_can_be_updated(api_client, user, tenant):
    website = Website.objects.create(tenant=tenant, url="https://acme.test", domain="acme.test", name="Acme")
    audit = Audit.objects.create(tenant=tenant, website=website, status=Audit.Status.COMPLETED, overall_score=70)
    issue = AuditIssue.objects.create(
        tenant=tenant,
        audit=audit,
        severity=AuditIssue.Severity.HIGH,
        category="on_page",
        title="Missing title tags",
        why_it_matters="x",
        evidence="y",
        recommendation="z",
    )
    api_client.force_authenticate(user=user)
    response = api_client.patch(
        f"/api/v1/audits/{audit.id}/issues/{issue.id}/",
        {"status": "resolved"},
        format="json",
        HTTP_X_TENANT_ID=str(tenant.id),
    )
    assert response.status_code == 200, response.data
    issue.refresh_from_db()
    assert issue.status == "resolved"


@pytest.mark.django_db
def test_audit_quota_is_enforced(api_client, user, tenant):
    from apps.billing.models import Subscription

    subscription = Subscription.objects.filter(tenant=tenant).select_related("plan").first()
    subscription.plan.max_audits_per_month = 1
    subscription.plan.save(update_fields=["max_audits_per_month"])
    website = Website.objects.create(tenant=tenant, url="https://acme.test", domain="acme.test", name="Acme")
    Audit.objects.create(tenant=tenant, website=website, status=Audit.Status.COMPLETED)
    api_client.force_authenticate(user=user)
    with patch("workers.tasks.run_website_audit.delay"):
        response = api_client.post(f"/api/v1/websites/{website.id}/audit/", HTTP_X_TENANT_ID=str(tenant.id))
    assert response.status_code == 402


@pytest.mark.django_db
def test_audit_report_includes_grouped_issues(api_client, user, tenant):
    website = Website.objects.create(tenant=tenant, url="https://acme.test", domain="acme.test", name="Acme")
    audit = Audit.objects.create(
        tenant=tenant,
        website=website,
        status=Audit.Status.COMPLETED,
        overall_score=81,
        scores={"technical_seo": 80, "aeo": 70},
        summary={"https": True},
    )
    AuditIssue.objects.create(
        tenant=tenant,
        audit=audit,
        severity="medium",
        category="on_page",
        title="Missing meta descriptions",
        why_it_matters="x",
        evidence="y",
        recommendation="z",
    )
    api_client.force_authenticate(user=user)
    response = api_client.get(f"/api/v1/audits/{audit.id}/report/", HTTP_X_TENANT_ID=str(tenant.id))
    assert response.status_code == 200
    assert response.data["website"]["domain"] == "acme.test"
    assert "on_page" in response.data["issues_by_category"]
