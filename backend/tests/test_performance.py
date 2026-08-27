from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest

from apps.audits.analysis import analyze_crawl
from apps.audits.models import Audit, Crawl, CrawlPage
from apps.audits.performance import build_performance_snapshot, compare_snapshots, detect_regression, score_page
from apps.audits.performance_config import resolve_performance_config, threshold_score
from apps.crawler.fetcher import fetch_url, network_snapshot
from apps.crawler.metrics import compression_kind, is_compressible
from apps.crawler.parser import parse_html
from apps.websites.models import Website


HTML = """
<html lang="en">
<head>
  <title>Acme pumps</title>
  <meta name="description" content="Industrial pumps" />
  <link rel="stylesheet" href="/app.css" />
  <script src="/app.js"></script>
  <link rel="preconnect" href="https://cdn.example.com" />
</head>
<body>
  <h1>Pumps</h1>
  <img src="/hero.jpg" alt="Pump" />
  <img src="/gallery.jpg" />
  <script src="https://ads.example.com/tag.js"></script>
</body>
</html>
"""


def test_compression_and_thresholds():
    assert compression_kind("br, gzip") == "brotli"
    assert compression_kind("gzip") == "gzip"
    assert compression_kind("") == "none"
    assert is_compressible("text/html") is True
    assert is_compressible("image/jpeg") is False
    assert threshold_score(180, {"excellent": 200, "good": 500, "needs_improvement": 800, "poor": 1800}) == 100
    assert threshold_score(900, {"excellent": 200, "good": 500, "needs_improvement": 800, "poor": 1800}) == 35


def test_parser_collects_resources():
    extracted = parse_html("https://acme.test/", HTML)
    summary = extracted["resource_summary"]
    assert summary["js"] >= 2
    assert summary["css"] >= 1
    assert summary["images"] >= 2
    assert summary["third_party"] >= 1
    assert summary["hints"]["preconnect"] >= 1
    assert extracted["title_length"] > 0


def test_fetch_records_ttfb_from_elapsed():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "text/html; charset=utf-8", "content-encoding": "gzip"}
    mock_response.content = b"<html><body>ok</body></html>"
    mock_response.elapsed = timedelta(milliseconds=180)
    mock_response.url = "https://acme.test/"
    mock_response.encoding = "utf-8"
    mock_response.http_version = "HTTP/1.1"
    mock_response.num_bytes_downloaded = 40
    with patch("apps.crawler.fetcher.validate_public_http_url", return_value="https://acme.test/"):
        with patch(
            "apps.crawler.fetcher.resolve_pinned_target",
            return_value=("https://93.184.216.34/", "acme.test", "acme.test"),
        ):
            with patch("apps.crawler.fetcher.httpx.Client") as client_cls:
                client_cls.return_value.__enter__.return_value.get.return_value = mock_response
                result = fetch_url("https://acme.test/")
    assert result.ttfb_ms == 180
    assert result.status_code == 200
    snap = network_snapshot(result)
    assert snap["ttfb_ms"] == 180
    assert snap["compression"] == "gzip"
    assert snap["timing_source"] == "crawl"


@pytest.mark.django_db
def test_performance_snapshot_uses_real_ttfb(tenant):
    website = Website.objects.create(tenant=tenant, url="https://acme.test", domain="acme.test", name="Acme")
    crawl = Crawl.objects.create(tenant=tenant, website=website, status=Crawl.Status.COMPLETED, signals={"https": True})
    extracted = parse_html("https://acme.test/", HTML)
    extracted.update(
        {
            "ttfb_ms": 920,
            "elapsed_ms": 1100,
            "html_size_bytes": 18000,
            "size_bytes": 18000,
            "transfer_bytes": 6000,
            "compression": "none",
            "content_type": "text/html",
            "https": True,
            "http_protocol": "HTTP/1.1",
            "redirect_count": 3,
            "redirect_hops": [
                {"url": "http://acme.test", "status": 301},
                {"url": "https://acme.test", "status": 301},
                {"url": "https://www.acme.test", "status": 301},
            ],
        }
    )
    page = CrawlPage.objects.create(
        tenant=tenant,
        crawl=crawl,
        url="https://www.acme.test/",
        status_code=200,
        title="Acme",
        extracted=extracted,
        ttfb_ms=920,
        html_size_bytes=18000,
    )
    snapshot = build_performance_snapshot([page], website=website)
    assert snapshot["kpis"]["median_ttfb_ms"] == 920
    assert snapshot["timing_source"] == "crawl"
    codes = {item["code"] for item in snapshot["issues"]}
    assert "PERF_TTFB_HIGH" in codes
    assert "PERF_REDIRECT_CHAIN" in codes
    assert "PERF_NO_COMPRESSION" not in codes or extracted["html_size_bytes"] > 50_000
    scored = score_page(extracted, 200, resolve_performance_config(website))
    assert 0 <= scored["score"] <= 100


@pytest.mark.django_db
def test_analyze_crawl_writes_performance_snapshot(tenant):
    website = Website.objects.create(tenant=tenant, url="https://acme.test", domain="acme.test", name="Acme")
    crawl = Crawl.objects.create(
        tenant=tenant,
        website=website,
        status=Crawl.Status.COMPLETED,
        signals={"https": True, "robots_txt": {"found": True}, "sitemap": {"found": True, "url_count": 4}},
    )
    extracted = parse_html("https://acme.test/", HTML)
    extracted.update(
        {
            "elapsed_ms": 220,
            "ttfb_ms": 180,
            "size_bytes": 12000,
            "html_size_bytes": 12000,
            "redirect_count": 0,
            "https": True,
            "hsts": True,
            "compression": "gzip",
            "content_encoding": "gzip",
            "http_protocol": "HTTP/2",
            "json_ld": True,
            "json_ld_types": ["Organization"],
        }
    )
    CrawlPage.objects.create(tenant=tenant, crawl=crawl, url="https://acme.test/", status_code=200, title=extracted["title"], extracted=extracted)
    audit = Audit.objects.create(tenant=tenant, website=website, crawl=crawl, status=Audit.Status.RUNNING)
    analyze_crawl(audit, crawl)
    audit.refresh_from_db()
    assert audit.summary["performance"]["technical_score"] >= 1
    assert "technical_performance" in audit.scores
    assert audit.scores["performance"] == audit.summary["performance"]["overall_score"]


@pytest.mark.django_db
def test_regression_and_compare():
    previous = {"overall_score": 80, "technical_score": 82, "ux_score": None, "kpis": {"median_ttfb_ms": 400, "median_html_bytes": 100000, "redirect_pages": 1, "error_pages": 0, "compression_rate": 90}, "distributions": {"resources": {"js": 4}}, "issues": [{"code": "PERF_HTTP1"}]}
    current = {"overall_score": 70, "technical_score": 71, "ux_score": None, "kpis": {"median_ttfb_ms": 900, "median_html_bytes": 140000, "redirect_pages": 4, "error_pages": 2, "compression_rate": 60}, "distributions": {"resources": {"js": 9}}, "issues": [{"code": "PERF_TTFB_HIGH"}]}
    cfg = resolve_performance_config()
    result = detect_regression(current, previous, cfg)
    assert result["detected"] is True
    compared = compare_snapshots(current, previous)
    assert compared["available"] is True
    assert "PERF_TTFB_HIGH" in compared["new_issue_codes"]


@pytest.mark.django_db
def test_performance_api_is_tenant_scoped(api_client, user, tenant, other_tenant, other_user):
    website = Website.objects.create(tenant=tenant, url="https://acme.test", domain="acme.test", name="Acme")
    audit = Audit.objects.create(
        tenant=tenant,
        website=website,
        status=Audit.Status.COMPLETED,
        overall_score=80,
        scores={"performance": 80, "technical_performance": 82},
        summary={"performance": {"overall_score": 80, "technical_score": 82, "kpis": {"median_ttfb_ms": 210}, "issues": []}},
    )
    api_client.force_authenticate(user=other_user)
    blocked = api_client.get(f"/api/v1/audits/{audit.id}/performance/", HTTP_X_TENANT_ID=str(other_tenant.id))
    assert blocked.status_code in {403, 404}
    api_client.force_authenticate(user=user)
    allowed = api_client.get(f"/api/v1/audits/{audit.id}/performance/", HTTP_X_TENANT_ID=str(tenant.id))
    assert allowed.status_code == 200
    assert allowed.data["scores"]["overall"] == 80
    pages = api_client.get(
        f"/api/v1/audits/{audit.id}/pages/",
        {"ordering": "-ttfb_ms", "page": 1, "page_size": 25},
        HTTP_X_TENANT_ID=str(tenant.id),
    )
    assert pages.status_code == 200
    assert "results" in pages.data


@pytest.mark.django_db
def test_audit_pages_list_orders_by_ttfb(api_client, user, tenant):
    website = Website.objects.create(tenant=tenant, url="https://acme.test", domain="acme.test", name="Acme")
    crawl = Crawl.objects.create(tenant=tenant, website=website, status=Crawl.Status.COMPLETED)
    slow = CrawlPage.objects.create(
        tenant=tenant,
        crawl=crawl,
        url="https://acme.test/slow",
        status_code=200,
        title="Slow",
        ttfb_ms=1400,
        html_size_bytes=8000,
        page_score=40,
    )
    CrawlPage.objects.create(
        tenant=tenant,
        crawl=crawl,
        url="https://acme.test/fast",
        status_code=200,
        title="Fast",
        ttfb_ms=180,
        html_size_bytes=4000,
        page_score=90,
    )
    audit = Audit.objects.create(tenant=tenant, website=website, crawl=crawl, status=Audit.Status.COMPLETED)
    api_client.force_authenticate(user=user)
    response = api_client.get(
        f"/api/v1/audits/{audit.id}/pages/",
        {"ordering": "-ttfb_ms", "page": 1, "page_size": 25},
        HTTP_X_TENANT_ID=str(tenant.id),
    )
    assert response.status_code == 200
    urls = [row["url"] for row in response.data["results"]]
    assert urls[0] == slow.url
    detail = api_client.get(f"/api/v1/audits/{audit.id}/pages/{slow.id}/", HTTP_X_TENANT_ID=str(tenant.id))
    assert detail.status_code == 200
    assert detail.data["id"] == str(slow.id)


@pytest.mark.django_db
def test_dashboard_includes_performance_score(api_client, user, tenant):
    website = Website.objects.create(tenant=tenant, url="https://acme.test", domain="acme.test", name="Acme")
    Audit.objects.create(
        tenant=tenant,
        website=website,
        status=Audit.Status.COMPLETED,
        overall_score=81,
        scores={"performance": 77, "technical_performance": 79, "opportunity": 60},
    )
    api_client.force_authenticate(user=user)
    response = api_client.get("/api/v1/dashboard/overview/", HTTP_X_TENANT_ID=str(tenant.id))
    assert response.status_code == 200
    assert response.data["intelligence"]["performance_score"] == 77
