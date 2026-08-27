from __future__ import annotations

import logging
from collections import Counter, defaultdict
from statistics import median

from apps.audits.models import Audit, AuditIssue, AuditRecommendation
from apps.audits.performance_config import band_label, resolve_performance_config, threshold_score
from apps.crawler.metrics import is_compressible

logger = logging.getLogger("sipulse.performance")


def _clamp(value: float) -> int:
    return int(max(0, min(100, round(value))))


def _percentile(values: list[float], pct: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((pct / 100) * (len(ordered) - 1)))))
    return int(ordered[index])


def page_ttfb(extracted: dict) -> int:
    return int(extracted.get("ttfb_ms") or extracted.get("elapsed_ms") or 0)


def page_html_bytes(extracted: dict) -> int:
    return int(extracted.get("html_size_bytes") or extracted.get("size_bytes") or 0)


def _summary(extracted: dict) -> dict:
    return extracted.get("resource_summary") or {}


def score_page(extracted: dict, status_code: int | None, cfg: dict) -> dict:
    weights = cfg["weights"]
    ttfb = page_ttfb(extracted)
    html_bytes = page_html_bytes(extracted)
    total_ms = int(extracted.get("elapsed_ms") or ttfb)
    compression = str(extracted.get("compression") or "none")
    redirects = int(extracted.get("redirect_count") or 0)
    hops = extracted.get("redirect_hops") or []
    loop = any(item.get("loop") for item in hops if isinstance(item, dict))
    protocol = str(extracted.get("http_protocol") or "HTTP/1.1")
    cache = extracted.get("cache") or {}
    summary = _summary(extracted)
    compressible = is_compressible(str(extracted.get("content_type") or "text/html"))
    compression_score = 100
    if compressible and html_bytes > 1500:
        compression_score = {"brotli": 100, "gzip": 78, "deflate": 70, "none": 18}.get(compression, 40)
    redirect_score = 0 if loop else {0: 100, 1: 86, 2: 58}.get(redirects, 28)
    cache_score = 70
    if cache.get("no_store"):
        cache_score = 42
    elif cache.get("max_age") and int(cache.get("max_age") or 0) > 0:
        cache_score = 88
    elif extracted.get("etag") or extracted.get("last_modified"):
        cache_score = 76
    js_count = int(summary.get("js") or 0)
    resource_score = threshold_score(js_count, cfg["js_files"])
    third = int(summary.get("third_party") or 0)
    resource_score = _clamp((resource_score + threshold_score(third, cfg["third_party"])) / 2)
    protocol_score = {"HTTP/3": 100, "HTTP/2": 92, "HTTP/1.1": 62, "HTTP/1.0": 40}.get(protocol, 62)
    error_score = 100
    code = int(status_code or 200)
    if code >= 500:
        error_score = 8
    elif code >= 400:
        error_score = 28
    cdn_score = 90 if extracted.get("cdn") else 70
    https_score = 100 if extracted.get("https") else 10
    protocol_score = _clamp((protocol_score * 0.6) + (https_score * 0.4))
    parts = {
        "ttfb": threshold_score(ttfb, cfg["ttfb_ms"]),
        "response_time": threshold_score(total_ms, cfg["response_ms"]),
        "html_size": threshold_score(html_bytes, cfg["html_bytes"]),
        "compression": compression_score,
        "redirects": redirect_score,
        "caching": cache_score,
        "resource_weight": resource_score,
        "protocol": protocol_score,
        "errors": error_score,
        "cdn": cdn_score,
    }
    technical = 0.0
    weight_total = 0.0
    for key, score in parts.items():
        weight = float(weights.get(key) or 0)
        technical += score * weight
        weight_total += weight
    page_score = _clamp(technical / weight_total if weight_total else 0)
    return {"score": page_score, "parts": parts, "ttfb_ms": ttfb, "html_bytes": html_bytes, "total_ms": total_ms}


def _bucket_status(code: int | None) -> str:
    value = int(code or 0)
    if value in {200, 304}:
        return str(value)
    if value in {301, 302, 307, 308}:
        return str(value)
    if 400 <= value < 500:
        return "4xx"
    if value >= 500:
        return "5xx"
    return str(value or "other")


def build_performance_snapshot(pages, *, website=None, previous=None) -> dict:
    cfg = resolve_performance_config(website)
    ttfbs: list[float] = []
    html_sizes: list[float] = []
    totals: list[float] = []
    scores: list[int] = []
    compressions = Counter()
    protocols = Counter()
    statuses = Counter()
    redirect_pages = 0
    slow_pages: list[dict] = []
    fastest: list[dict] = []
    issues: list[dict] = []
    js_total = 0
    css_total = 0
    image_total = 0
    font_total = 0
    third_party = 0
    compressed_ok = 0
    compressible_pages = 0
    https_pages = 0
    hsts_pages = 0
    error_pages = 0
    explanations: list[str] = []

    for page in pages:
        extracted = page.extracted or {}
        scored = score_page(extracted, page.status_code, cfg)
        ttfb = scored["ttfb_ms"]
        html_bytes = scored["html_bytes"]
        ttfbs.append(ttfb)
        html_sizes.append(html_bytes)
        totals.append(scored["total_ms"])
        scores.append(scored["score"])
        compressions[str(extracted.get("compression") or "none")] += 1
        protocols[str(extracted.get("http_protocol") or "HTTP/1.1")] += 1
        statuses[_bucket_status(page.status_code)] += 1
        if int(extracted.get("redirect_count") or 0) >= 1:
            redirect_pages += 1
        summary = _summary(extracted)
        js_total += int(summary.get("js") or 0)
        css_total += int(summary.get("css") or 0)
        image_total += int(summary.get("images") or 0)
        font_total += int(summary.get("fonts") or 0)
        third_party += int(summary.get("third_party") or 0)
        if extracted.get("https"):
            https_pages += 1
        if extracted.get("hsts"):
            hsts_pages += 1
        if int(page.status_code or 200) >= 400:
            error_pages += 1
        if is_compressible(str(extracted.get("content_type") or "text/html")) and html_bytes > 1500:
            compressible_pages += 1
            if str(extracted.get("compression") or "none") != "none":
                compressed_ok += 1
        row = {"url": page.url, "ttfb_ms": ttfb, "html_bytes": html_bytes, "score": scored["score"], "status": page.status_code}
        slow_pages.append(row)
        fastest.append(row)
        issues.extend(_page_issues(page, extracted, scored, cfg))

    slow_pages = sorted(slow_pages, key=lambda item: item["ttfb_ms"], reverse=True)[:12]
    fastest = sorted(fastest, key=lambda item: item["ttfb_ms"])[:8]
    technical = _clamp(sum(scores) / len(scores)) if scores else 0
    ux = None
    ux_source = None
    ux_metrics = {}
    if pages:
        homepage = pages[0].extracted or {}
        ux_metrics = homepage.get("browser_ux") or {}
        if ux_metrics.get("available"):
            ux = int(ux_metrics.get("score") or 0)
            ux_source = ux_metrics.get("source") or "lab"
    weights = cfg["weights"]
    if ux is None:
        overall = technical
        overall_note = "SIPulse Performance Score is 100% technical crawl data. Browser lab / field CWV was not available."
    else:
        overall = _clamp(technical * float(weights["technical"]) + ux * float(weights["ux"]))
        overall_note = (
            f"SIPulse Performance Score = {int(float(weights['technical']) * 100)}% technical crawl "
            f"+ {int(float(weights['ux']) * 100)}% UX / Core Web Vitals ({ux_source} data)."
        )
    avg_ttfb = int(sum(ttfbs) / len(ttfbs)) if ttfbs else 0
    median_ttfb = int(median(ttfbs)) if ttfbs else 0
    avg_html = int(sum(html_sizes) / len(html_sizes)) if html_sizes else 0
    compression_rate = round((compressed_ok / compressible_pages) * 100, 1) if compressible_pages else 100.0
    parts_avg = defaultdict(list)
    for page in pages:
        scored = score_page(page.extracted or {}, page.status_code, cfg)
        for key, value in scored["parts"].items():
            parts_avg[key].append(value)
    breakdown = {key: _clamp(sum(values) / len(values)) for key, values in parts_avg.items()}
    merged_issues = _merge_issues(issues)
    for item in merged_issues[:4]:
        explanations.append(item["title"])
    if median_ttfb >= int(cfg["ttfb_ms"]["needs_improvement"]):
        explanations.append("Slow TTFB")
    snapshot = {
        "overall_score": overall,
        "technical_score": technical,
        "ux_score": ux,
        "ux_source": ux_source,
        "ux_available": ux is not None,
        "band": band_label(overall, cfg),
        "technical_band": band_label(technical, cfg),
        "ux_band": band_label(ux, cfg) if ux is not None else "Unavailable",
        "weights": {"technical": weights["technical"], "ux": weights["ux"]},
        "breakdown": breakdown,
        "explain": {
            "overall": overall_note,
            "main_problems": list(dict.fromkeys(explanations))[:6],
            "data_sources": {
                "ttfb": "SIPulse Crawl",
                "html_size": "SIPulse Crawl",
                "compression": "SIPulse Crawl",
                "redirects": "SIPulse Crawl",
                "lcp": "Browser Lab" if ux_source == "lab" else ("Field Data" if ux_source == "field" else "Unavailable"),
            },
        },
        "kpis": {
            "median_ttfb_ms": median_ttfb,
            "avg_ttfb_ms": avg_ttfb,
            "p75_ttfb_ms": _percentile(ttfbs, 75),
            "p90_ttfb_ms": _percentile(ttfbs, 90),
            "p95_ttfb_ms": _percentile(ttfbs, 95),
            "avg_html_bytes": avg_html,
            "median_html_bytes": int(median(html_sizes)) if html_sizes else 0,
            "transfer_bytes": int(sum(int((page.extracted or {}).get("transfer_bytes") or page_html_bytes(page.extracted or {})) for page in pages)),
            "compression_rate": compression_rate,
            "redirect_pages": redirect_pages,
            "slow_pages": sum(1 for value in ttfbs if value >= int(cfg["ttfb_ms"]["needs_improvement"])),
            "error_pages": error_pages,
            "https_pages": https_pages,
            "hsts_pages": hsts_pages,
            "pages": len(pages),
        },
        "distributions": {
            "compression": dict(compressions),
            "protocol": dict(protocols),
            "status": dict(statuses),
            "resources": {"html": len(pages), "js": js_total, "css": css_total, "images": image_total, "fonts": font_total, "third_party": third_party},
        },
        "slowest": slow_pages,
        "fastest": fastest,
        "issues": merged_issues,
        "ux_metrics": ux_metrics,
        "thresholds": {
            "ttfb_ms": cfg["ttfb_ms"],
            "html_bytes": cfg["html_bytes"],
            "bands": cfg["bands"],
        },
        "timing_source": "crawl",
    }
    snapshot["regression"] = detect_regression(snapshot, previous, cfg) if previous else {"detected": False, "changes": []}
    return snapshot


def _page_issues(page, extracted: dict, scored: dict, cfg: dict) -> list[dict]:
    url = page.url
    items: list[dict] = []
    ttfb = scored["ttfb_ms"]
    html_bytes = scored["html_bytes"]
    summary = _summary(extracted)
    hops = extracted.get("redirect_hops") or []
    loop = any(item.get("loop") for item in hops if isinstance(item, dict))
    recommended_html = int(cfg["html_bytes"]["good"])
    if loop:
        items.append(_issue("PERF_REDIRECT_LOOP", "critical", "Redirect loop", url, f"{url} loops before a final response.", "Break the loop and serve a single canonical URL.", "critical"))
    if ttfb >= int(cfg["ttfb_ms"]["poor"]):
        items.append(_issue("PERF_TTFB_CRITICAL", "critical", "Critical TTFB", url, f"TTFB is {ttfb} ms (crawl). Critical threshold is {cfg['ttfb_ms']['poor']} ms.", "Review origin compute, database queries, application caching, and CDN origin shielding.", "high"))
    elif ttfb >= int(cfg["ttfb_ms"]["needs_improvement"]):
        items.append(_issue("PERF_TTFB_HIGH", "high", "Slow TTFB", url, f"TTFB is {ttfb} ms. Good is under {cfg['ttfb_ms']['good']} ms.", "Reduce server-side work before the first byte. Enable caching at the origin and CDN.", "high"))
    if scored["total_ms"] >= int(cfg["response_ms"]["poor"]):
        items.append(_issue("PERF_RESPONSE_SLOW", "high", "High total response time", url, f"Full HTML fetch took {scored['total_ms']} ms (TTFB {ttfb} ms + download {extracted.get('download_ms') or 0} ms).", "Cut HTML weight and origin time. This is crawl timing, not a lab Lighthouse score.", "high"))
    if html_bytes >= int(cfg["html_bytes"]["poor"]):
        over = round((html_bytes / recommended_html - 1) * 100)
        items.append(_issue("PERF_HTML_CRITICAL", "high", "Large HTML document", url, f"HTML is {html_bytes} bytes, {over}% above the {recommended_html} byte good target.", "Move non-critical markup out of the first response and paginate large tables.", "medium"))
    elif html_bytes >= int(cfg["html_bytes"]["needs_improvement"]):
        over = round((html_bytes / recommended_html - 1) * 100)
        items.append(_issue("PERF_HTML_LARGE", "medium", "Large HTML document", url, f"HTML is {html_bytes} bytes ({over}% above the {recommended_html} byte target).", "Reduce initial HTML. Defer below-the-fold content.", "medium"))
    encoding = str(extracted.get("compression") or "none")
    if is_compressible(str(extracted.get("content_type") or "text/html")) and html_bytes > 50_000 and encoding == "none":
        items.append(_issue("PERF_NO_COMPRESSION", "high", "No compression", url, f"{html_bytes} byte HTML response had no Content-Encoding.", "Enable Brotli (preferred) or gzip for HTML, CSS, and JavaScript. Do not recompress JPEG, PNG, WebP, AVIF, or MP4.", "low"))
    elif encoding == "gzip" and html_bytes > 80_000:
        items.append(_issue("PERF_GZIP_NOT_BROTLI", "low", "Gzip instead of Brotli", url, "HTML is gzip-compressed. Brotli typically transfers less on modern browsers.", "Enable Brotli at the CDN or origin for text responses, keeping gzip as a fallback.", "low"))
    if int(extracted.get("redirect_count") or 0) > 2:
        chain = " → ".join(str(item.get("url") or "") for item in hops) or " → ".join(extracted.get("hops") or [url])
        items.append(_issue("PERF_REDIRECT_CHAIN", "high", "Redirect chain", url, f"{extracted.get('redirect_count')} hop redirect chain: {chain}", "Point links and canonicals at the final URL. Keep at most one hop.", "medium"))
    elif int(extracted.get("redirect_count") or 0) == 2:
        items.append(_issue("PERF_REDIRECT_CHAIN", "medium", "2-hop redirect chain detected.", url, f"2-hop redirect chain detected for {url}.", "Collapse the chain to a single 301, or none.", "medium"))
    if any(int(item.get("status") or 0) in {302, 307} for item in hops if isinstance(item, dict)) and extracted.get("https"):
        items.append(_issue("PERF_REDIRECT_TEMPORARY", "medium", "Temporary redirect on a stable URL", url, "A 302/307 was used. Permanent destinations usually need 301 or 308.", "Switch stable canonical moves to 301/308.", "low"))
    if not extracted.get("https"):
        items.append(_issue("PERF_HTTP", "critical", "HTTP instead of HTTPS", url, f"{url} was fetched over HTTP.", "Redirect HTTP to HTTPS and install a valid certificate.", "medium"))
    if extracted.get("https") and not extracted.get("hsts"):
        items.append(_issue("PERF_NO_HSTS", "medium", "Missing HSTS", url, "No Strict-Transport-Security header on an HTTPS response.", "Add HSTS with a conservative max-age after HTTPS is stable. includeSubDomains and preload are optional.", "low"))
    if str(extracted.get("http_protocol") or "") == "HTTP/1.1":
        items.append(_issue("PERF_HTTP1", "info", "HTTP/1.1", url, "The crawl negotiated HTTP/1.1. HTTP/2 is typically faster for many assets. HTTP/3 absence is not a critical SEO issue.", "Enable HTTP/2 on the origin or CDN. Treat HTTP/3 as an enhancement, not a ranking requirement.", "low"))
    if int(summary.get("js") or 0) >= int(cfg["js_files"]["needs_improvement"]):
        items.append(_issue("PERF_JS_EXCESS", "medium", "Excessive JavaScript", url, f"{summary.get('js')} script files referenced in HTML.", "Combine or drop unused scripts. Defer non-critical JavaScript.", "medium"))
    if int(summary.get("css") or 0) >= 10:
        items.append(_issue("PERF_CSS_EXCESS", "low", "Excessive CSS", url, f"{summary.get('css')} stylesheets referenced.", "Bundle critical CSS and defer the rest.", "medium"))
    if int(summary.get("eager_images") or 0) >= 4 and int(summary.get("lazy_images") or 0) == 0:
        items.append(_issue("PERF_NO_LAZY", "medium", "Missing lazy loading", url, f"{summary.get('eager_images')} images without loading=lazy.", "Add loading=\"lazy\" to below-the-fold images. Keep the LCP image eager.", "low"))
    if int(summary.get("blocking_styles") or 0) >= 3:
        items.append(_issue("PERF_RENDER_BLOCK_CSS", "medium", "Render-blocking CSS", url, f"{summary.get('blocking_styles')} render-blocking stylesheets in HTML.", "Inline critical CSS and load the rest asynchronously.", "medium"))
    if int(summary.get("blocking_scripts") or 0) >= 1:
        items.append(_issue("PERF_RENDER_BLOCK_JS", "high", "Render-blocking JavaScript", url, f"{summary.get('blocking_scripts')} synchronous scripts in <head>.", "Add defer or async, or move scripts to the end of the body.", "medium"))
    hints = summary.get("hints") or {}
    if int(summary.get("third_party") or 0) >= 4 and int(hints.get("preconnect") or 0) == 0:
        items.append(_issue("PERF_NO_PRECONNECT", "low", "Missing preconnect", url, f"{summary.get('third_party')} third-party origins and no preconnect hints.", "Add rel=preconnect for the one or two origins on the critical path.", "low"))
    if int(summary.get("fonts") or 0) >= 2 and int(hints.get("preload") or 0) == 0:
        items.append(_issue("PERF_NO_PRELOAD", "low", "Missing preload", url, "Font files are referenced without a preload hint.", "Preload the primary font used in the first viewport.", "low"))
    cache = extracted.get("cache") or {}
    ctype = str(extracted.get("content_type") or "")
    if "text/html" in ctype and cache.get("no_store"):
        items.append(_issue("PERF_CACHE_HTML", "info", "HTML marked no-store", url, "Cache-Control: no-store on HTML. That is sometimes correct for private pages.", "If this page is public, allow a short shared cache (s-maxage) at the CDN.", "low"))
    if int(summary.get("third_party") or 0) >= int(cfg["third_party"]["needs_improvement"]):
        items.append(_issue("PERF_THIRD_PARTY", "medium", "Excessive third-party requests", url, f"{summary.get('third_party')} third-party resources in HTML.", "Remove unused tags and load remaining third parties after first paint.", "medium"))
    if int(summary.get("duplicates") or 0) >= 2:
        items.append(_issue("PERF_DUPLICATE_RESOURCES", "low", "Duplicate resources", url, f"{summary.get('duplicates')} duplicate resource URLs.", "Reference each script and stylesheet once.", "low"))
    if extracted.get("mixed_content"):
        items.append(_issue("PERF_MIXED_CONTENT", "high", "Mixed content", url, f"{len(extracted.get('mixed_content') or [])} http:// assets on an HTTPS page.", "Serve every script, image, and stylesheet over HTTPS.", "medium"))
    if int(page.status_code or 200) >= 500:
        items.append(_issue("PERF_5XX", "critical", "5xx response", url, f"Status {page.status_code} during the crawl.", "Fix the origin error. 5xx pages are not indexable and fail Core Web Vitals collection.", "high"))
    elif int(page.status_code or 200) >= 400:
        items.append(_issue("PERF_404", "high", "4xx resource/page", url, f"Status {page.status_code} during the crawl.", "Remove internal links to missing URLs or restore the document.", "medium"))
    if extracted.get("meta_refresh"):
        items.append(_issue("PERF_META_REFRESH", "medium", "Meta refresh redirect", url, f"meta refresh: {extracted.get('meta_refresh')}", "Replace client redirects with a single HTTP 301 to the final URL.", "low"))
    return items


def _issue(code: str, severity: str, title: str, url: str, evidence: str, recommendation: str, effort: str) -> dict:
    impact = {
        "critical": "Potential SEO impact: crawlers and users may never reach the intended document.",
        "high": "Potential SEO impact: slower crawls and weaker user experience signals.",
        "medium": "Potential SEO impact: extra latency and wasted crawl budget.",
        "low": "Optimization opportunity. Do not treat this as a guaranteed ranking change.",
        "info": "Informational. Not a ranking claim.",
    }.get(severity, "Potential SEO impact.")
    return {
        "code": code,
        "category": "performance",
        "severity": severity,
        "title": title,
        "why_it_matters": impact,
        "affected_urls": [url],
        "evidence": evidence,
        "recommendation": recommendation,
        "estimated_effort": effort,
        "origin": "fact",
        "confidence": 1.0,
        "priority": {"critical": 96, "high": 82, "medium": 64, "low": 48, "info": 30}[severity],
        "impact": impact,
        "estimated_impact": effort,
        "documentation": code,
    }


def _merge_issues(items: list[dict]) -> list[dict]:
    grouped: dict[str, dict] = {}
    for item in items:
        key = item["code"]
        if key not in grouped:
            grouped[key] = dict(item)
            grouped[key]["affected_urls"] = list(item.get("affected_urls") or [])
            continue
        grouped[key]["affected_urls"] = list(dict.fromkeys(grouped[key]["affected_urls"] + (item.get("affected_urls") or [])))[:40]
        grouped[key]["evidence"] = f"{grouped[key]['evidence']} {item['evidence']}"[:1500]
    return sorted(grouped.values(), key=lambda item: (-item["priority"], item["code"]))


def detect_regression(current: dict, previous: dict | None, cfg: dict) -> dict:
    if not previous:
        return {"detected": False, "changes": []}
    limits = cfg["regression"]
    changes = []
    cur_k = current.get("kpis") or {}
    prev_k = previous.get("kpis") or {}

    def pct(new, old) -> float | None:
        if not old:
            return None
        return round(((new - old) / old) * 100, 1)

    checks = [
        ("ttfb", cur_k.get("median_ttfb_ms") or 0, prev_k.get("median_ttfb_ms") or 0, limits["ttfb_pct"], True, "TTFB increased"),
        ("html", cur_k.get("median_html_bytes") or 0, prev_k.get("median_html_bytes") or 0, limits["html_pct"], True, "HTML size increased"),
        ("js", (current.get("distributions") or {}).get("resources", {}).get("js") or 0, (previous.get("distributions") or {}).get("resources", {}).get("js") or 0, limits["js_pct"], True, "JavaScript payload increased"),
        ("score", current.get("overall_score") or 0, previous.get("overall_score") or 0, limits["score_points"], False, "Performance score decreased"),
        ("cwv", current.get("ux_score") or 0, previous.get("ux_score") or 0, limits["cwv_points"], False, "CWV score decreased"),
        ("errors", cur_k.get("error_pages") or 0, prev_k.get("error_pages") or 0, 0, True, "5xx/4xx errors increased"),
        ("redirects", cur_k.get("redirect_pages") or 0, prev_k.get("redirect_pages") or 0, 0, True, "Redirect chains increased"),
    ]
    detected = False
    for key, new, old, limit, higher_worse, label in checks:
        if old in (None, 0) and key in {"cwv"}:
            continue
        if higher_worse:
            delta_pct = pct(new, old)
            worse = new > old and (limit == 0 and new > old or (delta_pct is not None and delta_pct >= limit))
            change = {"metric": key, "previous": old, "current": new, "change": new - old, "change_pct": delta_pct, "label": label, "regression": worse}
        else:
            drop = (old or 0) - (new or 0)
            worse = drop >= limit and (old or 0) > 0
            change = {"metric": key, "previous": old, "current": new, "change": new - old, "change_pct": pct(new, old), "label": label, "regression": worse}
        changes.append(change)
        if change["regression"]:
            detected = True
    return {"detected": detected, "changes": changes, "message": "Performance regression detected." if detected else ""}


def compare_snapshots(current: dict, previous: dict | None) -> dict:
    if not previous:
        return {"available": False, "rows": [], "improvements": [], "regressions": [], "new_issue_codes": [], "resolved_issue_codes": []}
    rows = []
    pairs = [
        ("Performance", current.get("overall_score"), previous.get("overall_score"), "points"),
        ("Technical", current.get("technical_score"), previous.get("technical_score"), "points"),
        ("UX / CWV", current.get("ux_score"), previous.get("ux_score"), "points"),
        ("TTFB median", (current.get("kpis") or {}).get("median_ttfb_ms"), (previous.get("kpis") or {}).get("median_ttfb_ms"), "ms"),
        ("HTML size median", (current.get("kpis") or {}).get("median_html_bytes"), (previous.get("kpis") or {}).get("median_html_bytes"), "bytes"),
        ("Redirects", (current.get("kpis") or {}).get("redirect_pages"), (previous.get("kpis") or {}).get("redirect_pages"), "count"),
        ("Compression", (current.get("kpis") or {}).get("compression_rate"), (previous.get("kpis") or {}).get("compression_rate"), "%"),
        ("LCP", ((current.get("ux_metrics") or {}).get("lcp_ms")), ((previous.get("ux_metrics") or {}).get("lcp_ms")), "ms"),
    ]
    improvements = []
    regressions = []
    for label, new, old, unit in pairs:
        if new is None or old is None:
            rows.append({"metric": label, "previous": old, "current": new, "change": None, "change_pct": None, "unit": unit})
            continue
        change = new - old
        pct = round((change / old) * 100, 1) if old else None
        rows.append({"metric": label, "previous": old, "current": new, "change": change, "change_pct": pct, "unit": unit})
        lower_better = unit in {"ms", "bytes", "count"}
        better = change < 0 if lower_better else change > 0
        if change == 0:
            continue
        (improvements if better else regressions).append(label)
    current_codes = {item["code"] for item in current.get("issues") or []}
    previous_codes = {item["code"] for item in previous.get("issues") or []}
    return {
        "available": True,
        "rows": rows,
        "improvements": improvements,
        "regressions": regressions,
        "new_issue_codes": sorted(current_codes - previous_codes),
        "resolved_issue_codes": sorted(previous_codes - current_codes),
    }


def apply_performance_issues(audit: Audit, snapshot: dict) -> None:
    existing = set(audit.issues.filter(category="performance").values_list("title", flat=True))
    for item in snapshot.get("issues") or []:
        if item["title"] in existing:
            continue
        severity = item["severity"]
        valid = {choice[0] for choice in AuditIssue.Severity.choices}
        if severity not in valid:
            severity = AuditIssue.Severity.LOW
        issue = AuditIssue.objects.create(
            tenant=audit.tenant,
            audit=audit,
            code=item["code"],
            severity=severity,
            category="performance",
            title=item["title"],
            why_it_matters=item["why_it_matters"],
            affected_urls=item["affected_urls"],
            evidence=item["evidence"],
            recommendation=item["recommendation"],
            estimated_effort=item["estimated_effort"],
            origin="fact",
            confidence=1.0,
            priority=item["priority"],
        )
        AuditRecommendation.objects.create(
            tenant=audit.tenant,
            audit=audit,
            issue=issue,
            title=issue.title,
            verified_finding=issue.evidence,
            ai_interpretation="",
            recommendation=issue.recommendation,
            origin="recommendation",
            confidence=1.0,
        )
    if (snapshot.get("regression") or {}).get("detected"):
        issue = AuditIssue.objects.create(
            tenant=audit.tenant,
            audit=audit,
            code="PERF_REGRESSION",
            severity=AuditIssue.Severity.HIGH,
            category="performance",
            title="Performance regression detected.",
            why_it_matters="This crawl is materially worse than the previous crawl on one or more SIPulse performance metrics.",
            affected_urls=[],
            evidence="; ".join(item["label"] for item in snapshot["regression"]["changes"] if item.get("regression")),
            recommendation="Compare this crawl with the previous crawl and fix the regressed metrics before they become the new baseline.",
            estimated_effort="high",
            origin="fact",
            confidence=1.0,
            priority=90,
        )
        AuditRecommendation.objects.create(
            tenant=audit.tenant,
            audit=audit,
            issue=issue,
            title=issue.title,
            verified_finding=issue.evidence,
            ai_interpretation="",
            recommendation=issue.recommendation,
            origin="recommendation",
            confidence=1.0,
        )


def enrich_performance_recommendations(audit: Audit) -> None:
    from apps.platform.lead_sources import resolve_ai_adapters
    from providers.ai.base import ProviderUnavailable
    from services.ai_gateway import AIService

    if not resolve_ai_adapters():
        return
    recs = (
        AuditRecommendation.objects.filter(audit=audit, issue__category="performance")
        .select_related("issue")
        .order_by("-issue__priority")[:5]
    )
    for rec in recs:
        if rec.ai_interpretation:
            continue
        try:
            result = AIService.complete(
                tenant=audit.tenant,
                user=None,
                task="perf_recommendation",
                prompt=(
                    "Write one short operator paragraph. Use only the evidence below. "
                    "Do not invent timings, scores, URLs, or Core Web Vitals. "
                    "Do not treat Lighthouse as the source of SIPulse scores. "
                    'Return JSON {"guidance": "..."}.'
                ),
                untrusted=f"Title: {rec.title}\nEvidence: {rec.verified_finding}\nRecommendation: {rec.recommendation}",
                schema={"type": "object"},
            )
        except ProviderUnavailable:
            return
        except Exception:  # noqa: BLE001
            logger.info("perf_ai_enrich_failed audit=%s", audit.id)
            return
        text = str((result or {}).get("guidance") or (result or {}).get("text") or "").strip()
        if not text:
            continue
        rec.ai_interpretation = text[:2000]
        rec.save(update_fields=["ai_interpretation", "updated_at"])


def page_api_payload(page) -> dict:
    extracted = page.extracted or {}
    summary = _summary(extracted)
    hops = extracted.get("redirect_hops") or []
    return {
        "id": str(page.id),
        "url": page.url,
        "status_code": page.status_code,
        "title": page.title,
        "ttfb_ms": page.ttfb_ms if getattr(page, "ttfb_ms", None) is not None else page_ttfb(extracted),
        "html_size_bytes": page.html_size_bytes or page_html_bytes(extracted),
        "transfer_bytes": page.transfer_bytes or int(extracted.get("transfer_bytes") or 0),
        "redirect_count": int(extracted.get("redirect_count") or 0),
        "compression": page.compression or extracted.get("compression") or "none",
        "http_protocol": page.http_protocol or extracted.get("http_protocol") or "",
        "page_score": page.page_score,
        "https": bool(extracted.get("https")),
        "cdn": extracted.get("cdn") or "",
        "timing_source": "crawl",
        "lcp_ms": (extracted.get("browser_ux") or {}).get("lcp_ms"),
        "inp_ms": (extracted.get("browser_ux") or {}).get("inp_ms"),
        "cls": (extracted.get("browser_ux") or {}).get("cls"),
        "cwv_source": (extracted.get("browser_ux") or {}).get("source"),
        "updated_at": page.updated_at,
        "resource_summary": summary,
        "redirect_hops": hops,
    }


def page_detail_payload(page) -> dict:
    extracted = page.extracted or {}
    payload = page_api_payload(page)
    timing = extracted.get("timing") or {}
    payload.update(
        {
            "timing": {
                "dns_ms": timing.get("dns_ms"),
                "tcp_ms": timing.get("tcp_ms"),
                "tls_ms": timing.get("tls_ms"),
                "ttfb_ms": page_ttfb(extracted),
                "download_ms": extracted.get("download_ms") or timing.get("download_ms"),
                "total_ms": extracted.get("elapsed_ms") or timing.get("total_ms"),
                "source": "crawl",
                "note": "DNS/TCP/TLS breakdown is included when the HTTP client exposes it. TTFB and total time are always crawl-measured.",
            },
            "response": {
                "status": page.status_code,
                "protocol": extracted.get("http_protocol"),
                "compression": extracted.get("compression"),
                "cache_control": extracted.get("cache_control"),
                "etag": extracted.get("etag"),
                "last_modified": extracted.get("last_modified"),
                "server": extracted.get("server"),
                "cdn": extracted.get("cdn"),
                "hsts": extracted.get("hsts_detail") or {"present": extracted.get("hsts")},
                "final_url": extracted.get("final_url") or page.url,
            },
            "resources": extracted.get("resources") or [],
            "mixed_content": extracted.get("mixed_content") or [],
            "cache": extracted.get("cache") or {},
        }
    )
    return payload
