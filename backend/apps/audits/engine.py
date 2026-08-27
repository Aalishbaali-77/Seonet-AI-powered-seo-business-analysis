from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from django.conf import settings
from django.utils import timezone

from apps.audits.models import Crawl, CrawlPage
from apps.billing.models import Subscription
from apps.crawler.fetcher import FetchResult, fetch_optional, fetch_url, network_snapshot
from apps.crawler.parser import parse_html
from apps.crawler.ssrf import SSRFBlocked, validate_public_http_url
from apps.jobs import services as job_services

SITEMAP_LOC_RE = re.compile(r"<loc>\s*([^<]+)\s*</loc>", re.I)


def plan_limits(tenant) -> tuple[int, int]:
    subscription = Subscription.objects.filter(tenant=tenant).select_related("plan").first()
    if subscription is None or subscription.plan_id is None:
        return 25, 20
    return int(subscription.plan.max_pages or 25), int(subscription.plan.max_audits_per_month or 20)


def _config(website) -> dict:
    max_pages, _ = plan_limits(website.tenant)
    defaults = {
        "max_pages": getattr(settings, "CRAWLER_MAX_PAGES", 20),
        "max_depth": getattr(settings, "CRAWLER_MAX_DEPTH", 3),
        "timeout": getattr(settings, "CRAWLER_TIMEOUT", 10),
        "max_response_size": getattr(settings, "CRAWLER_MAX_RESPONSE_SIZE", 2_000_000),
    }
    defaults.update(website.audit_config or {})
    defaults["max_pages"] = max(1, min(int(defaults["max_pages"] or 1), max_pages))
    defaults["max_depth"] = max(0, min(int(defaults["max_depth"] or 1), 8))
    return defaults


def _disallowed(url: str, disallow: list[str], seed: str) -> bool:
    if url == seed:
        return False
    path = urlparse(url).path or "/"
    for rule in disallow:
        if not rule or rule == "/":
            continue
        if path.startswith(rule):
            return True
    return False


def _origin(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def _page_payload(result: FetchResult, extracted: dict) -> dict:
    payload = dict(extracted)
    payload.update(network_snapshot(result))
    return payload


def _site_signals(seed: str, *, timeout: int) -> dict:
    origin = _origin(seed)
    robots = fetch_optional(urljoin(origin + "/", "robots.txt"), timeout=timeout)
    sitemaps: list[str] = []
    robots_found = bool(robots and robots.status_code == 200 and "html" not in (robots.content_type or ""))
    disallow: list[str] = []
    if robots_found and robots:
        for line in robots.body.splitlines():
            stripped = line.strip()
            lower = stripped.lower()
            if lower.startswith("sitemap:"):
                sitemaps.append(stripped.split(":", 1)[-1].strip())
            if lower.startswith("disallow:"):
                path = stripped.split(":", 1)[-1].strip()
                if path:
                    disallow.append(path)
    if not sitemaps:
        sitemaps = [urljoin(origin + "/", "sitemap.xml")]
    sitemap_hit = None
    loc_count = 0
    for sitemap_url in sitemaps[:4]:
        document = fetch_optional(sitemap_url, timeout=timeout)
        if document and document.status_code == 200 and "html" not in (document.content_type or ""):
            loc_count = len(SITEMAP_LOC_RE.findall(document.body))
            sitemap_hit = {"found": True, "url": sitemap_url, "status": document.status_code, "url_count": loc_count}
            break
    return {
        "https": seed.startswith("https://"),
        "robots_txt": {"found": robots_found, "status": robots.status_code if robots else None, "sitemaps": sitemaps, "disallow": disallow[:40]},
        "sitemap": sitemap_hit or {"found": False, "url": sitemaps[0] if sitemaps else "", "status": None, "url_count": 0},
    }


def crawl_website(website, *, job=None) -> Crawl:
    cfg = _config(website)
    crawl = Crawl.objects.create(tenant=website.tenant, website=website, job=job, status=Crawl.Status.RUNNING, started_at=timezone.now())
    seed = validate_public_http_url(website.url)
    crawl.signals = _site_signals(seed, timeout=int(cfg["timeout"]))
    crawl.save(update_fields=["signals", "updated_at"])
    disallow = list((crawl.signals.get("robots_txt") or {}).get("disallow") or [])
    queue: list[tuple[str, int]] = [(seed, 0)]
    seen: set[str] = set()
    crawled = 0
    max_pages = int(cfg["max_pages"])
    while queue and len(seen) < max_pages:
        url, depth = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        if _disallowed(url, disallow, seed):
            continue
        try:
            result = fetch_url(url, timeout=int(cfg["timeout"]), max_bytes=int(cfg["max_response_size"]))
            extracted = _page_payload(result, parse_html(result.url, result.body))
        except SSRFBlocked as exc:
            if url == seed:
                crawl.status = Crawl.Status.FAILED
                crawl.error = str(exc.detail)
                crawl.completed_at = timezone.now()
                crawl.save()
                raise
            continue
        CrawlPage.objects.create(
            tenant=website.tenant,
            crawl=crawl,
            url=result.url,
            status_code=result.status_code,
            title=extracted.get("title", "")[:500],
            content_type=result.content_type,
            extracted=extracted,
            origin="fact",
            ttfb_ms=int(extracted.get("ttfb_ms") or result.ttfb_ms or 0),
            html_size_bytes=int(extracted.get("html_size_bytes") or result.size_bytes or 0),
            transfer_bytes=int(extracted.get("transfer_bytes") or result.transfer_bytes or 0),
            compression=str(extracted.get("compression") or "")[:20],
            http_protocol=str(extracted.get("http_protocol") or "")[:20],
        )
        crawled += 1
        if job is not None:
            progress = 20 + int((crawled / max(max_pages, 1)) * 34)
            job_services.mark_progress(
                job,
                progress=min(progress, 54),
                result={"stage": "Crawling", "pages_crawled": crawled, "pages_discovered": crawled},
            )
        if depth < int(cfg["max_depth"]) and len(seen) + len(queue) < max_pages:
            for link in extracted.get("internal_links", []):
                if _disallowed(link, disallow, seed):
                    continue
                if link not in seen and all(link != item[0] for item in queue):
                    queue.append((link, depth + 1))
    crawl.pages_discovered = crawl.pages.count()
    crawl.status = Crawl.Status.COMPLETED
    crawl.completed_at = timezone.now()
    crawl.save()
    return crawl
