from __future__ import annotations

from collections import Counter

from django.utils import timezone

from apps.audits.models import Audit, AuditIssue, AuditRecommendation, Crawl


def _clamp(value: float) -> int:
    return int(max(0, min(100, round(value))))


def _add_issue(audit, **kwargs) -> AuditIssue:
    issue = AuditIssue.objects.create(tenant=audit.tenant, audit=audit, **kwargs)
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
    return issue


def _urls(pages, predicate) -> list[str]:
    return [page.url for page in pages if predicate(page)]


def _meta(page, key: str) -> str:
    return str((page.extracted.get("meta") or {}).get(key) or "").strip()


def _heading_skip(extracted: dict) -> bool:
    present = []
    headings = extracted.get("headings") or {}
    for level in range(1, 7):
        if headings.get(f"h{level}") or (level == 1 and extracted.get("h1")):
            present.append(level)
    return any(present[index] - present[index - 1] > 1 for index in range(1, len(present)))


def analyze_crawl(audit: Audit, crawl: Crawl) -> Audit:
    pages = list(crawl.pages.all())
    audit.pages_crawled = len(pages)
    if not pages:
        audit.status = Audit.Status.FAILED
        audit.summary = {"error": "No HTML pages were crawled."}
        audit.save()
        return audit

    website = audit.website
    signals = crawl.signals or {}
    homepage = pages[0]
    keywords = [str(item).strip().lower() for item in (website.keywords or []) if str(item).strip()]
    markets = [str(item).strip().lower() for item in (website.target_markets or []) if str(item).strip()]

    missing_title = _urls(pages, lambda page: not page.title)
    short_title = _urls(pages, lambda page: 0 < len(page.title) < 15)
    long_title = _urls(pages, lambda page: len(page.title) > 65)
    duplicate_titles = [title for title, count in Counter(page.title for page in pages if page.title).items() if count > 1]
    missing_desc = _urls(pages, lambda page: not _meta(page, "description"))
    short_desc = _urls(pages, lambda page: 0 < len(_meta(page, "description")) < 50)
    missing_canonical = _urls(pages, lambda page: not page.extracted.get("canonical"))
    missing_h1 = _urls(pages, lambda page: not page.extracted.get("h1"))
    multiple_h1 = _urls(pages, lambda page: len(page.extracted.get("h1") or []) > 1)
    missing_og = _urls(pages, lambda page: not _meta(page, "og:title"))
    missing_twitter = _urls(pages, lambda page: not _meta(page, "twitter:card"))
    missing_viewport = _urls(pages, lambda page: not page.extracted.get("has_viewport"))
    missing_lang = _urls(pages, lambda page: not page.extracted.get("html_lang"))
    thin_pages = _urls(pages, lambda page: int(page.extracted.get("word_count") or 0) < 150)
    heading_skips = _urls(pages, lambda page: _heading_skip(page.extracted or {}))
    mixed = [url for page in pages for url in (page.extracted.get("mixed_content") or [])]
    json_ld_pages = _urls(pages, lambda page: page.extracted.get("json_ld"))
    schema_types = sorted({item for page in pages for item in (page.extracted.get("json_ld_types") or [])})
    alt_missing = sum(int(page.extracted.get("images_missing_alt") or 0) for page in pages)
    error_pages = _urls(pages, lambda page: int(page.status_code or 200) >= 400)
    slow_pages = _urls(pages, lambda page: int((page.extracted or {}).get("ttfb_ms") or page.extracted.get("elapsed_ms") or 0) >= 1500)
    heavy_pages = _urls(pages, lambda page: int(page.extracted.get("size_bytes") or 0) >= 500_000)
    uncompressed = _urls(pages, lambda page: not page.extracted.get("content_encoding") and int(page.extracted.get("size_bytes") or 0) > 50_000)
    redirect_heavy = _urls(pages, lambda page: int(page.extracted.get("redirect_count") or 0) >= 2)
    noindex = _urls(
        pages,
        lambda page: "noindex" in f"{_meta(page, 'robots')} {page.extracted.get('x_robots_tag') or ''}".lower(),
    )
    https_ok = all(page.extracted.get("https") for page in pages) and bool(signals.get("https", True))
    hsts = any(page.extracted.get("hsts") for page in pages)
    robots_found = bool((signals.get("robots_txt") or {}).get("found"))
    sitemap = signals.get("sitemap") or {}
    sitemap_found = bool(sitemap.get("found") or sitemap.get("url_count"))
    aeo_types = {"FAQPage", "QAPage", "HowTo", "Article", "WebSite", "Organization"}
    local_types = {"LocalBusiness", "Organization", "Restaurant", "Store", "ProfessionalService"}
    geo_types = {"GeoCoordinates", "Place", "PostalAddress", "LocalBusiness"}
    has_aeo_schema = bool(aeo_types.intersection(schema_types))
    has_local_schema = bool(local_types.intersection(schema_types))
    has_geo_schema = bool(geo_types.intersection(schema_types))
    phones = [item for page in pages for item in (page.extracted.get("phones") or [])]
    emails = [item for page in pages for item in (page.extracted.get("emails") or [])]
    addresses = [item for page in pages for item in (page.extracted.get("address_text") or [])]
    nap = bool(phones and (emails or addresses or has_local_schema))
    hreflang = [item for page in pages for item in (page.extracted.get("hreflang") or [])]
    homepage_text = " ".join(
        [
            homepage.title,
            " ".join(homepage.extracted.get("h1") or []),
            _meta(homepage, "description"),
        ]
    ).lower()
    keyword_hits = [word for word in keywords if word in homepage_text]
    market_hits = [market for market in markets if market in homepage_text or market in " ".join(hreflang).lower()]

    if not https_ok:
        _add_issue(
            audit,
            severity=AuditIssue.Severity.CRITICAL,
            category="technical",
            title="Site is not fully served over HTTPS",
            why_it_matters="Browsers, search engines, and AI crawlers treat HTTP as insecure and may suppress the site.",
            affected_urls=_urls(pages, lambda page: not page.extracted.get("https")) or [homepage.url],
            evidence="One or more crawled URLs used http:// instead of https://.",
            recommendation="Redirect all HTTP URLs to HTTPS, install a valid certificate, and enable HSTS once HTTPS is stable.",
            estimated_effort="medium",
            origin="fact",
            confidence=1.0,
            priority=98,
        )
    if error_pages:
        _add_issue(
            audit,
            severity=AuditIssue.Severity.HIGH,
            category="technical",
            title="Crawled pages returned HTTP errors",
            why_it_matters="4xx and 5xx responses waste crawl budget and hide content from search and answer engines.",
            affected_urls=error_pages,
            evidence=f"{len(error_pages)} crawled URLs returned status 400 or higher.",
            recommendation="Fix or redirect broken URLs. Keep only live 200 pages in internal links and sitemaps.",
            estimated_effort="medium",
            origin="fact",
            confidence=1.0,
            priority=92,
        )
    if not robots_found:
        _add_issue(
            audit,
            severity=AuditIssue.Severity.MEDIUM,
            category="technical",
            title="robots.txt was not found",
            why_it_matters="A robots.txt file tells crawlers what they may fetch and where the sitemap lives.",
            affected_urls=[homepage.url],
            evidence="GET /robots.txt did not return a plain-text robots file.",
            recommendation="Publish https://{host}/robots.txt with at least a Sitemap line pointing at your XML sitemap.".format(
                host=website.domain
            ),
            estimated_effort="low",
            origin="fact",
            confidence=1.0,
            priority=72,
        )
    if not sitemap_found:
        _add_issue(
            audit,
            severity=AuditIssue.Severity.HIGH,
            category="technical",
            title="XML sitemap was not found",
            why_it_matters="Sitemaps help search and AI crawlers discover every indexable URL.",
            affected_urls=[homepage.url],
            evidence="No usable sitemap.xml (or Sitemap: entry in robots.txt) was found.",
            recommendation="Generate an XML sitemap of canonical URLs and list it in robots.txt.",
            estimated_effort="low",
            origin="fact",
            confidence=1.0,
            priority=84,
        )
    if missing_canonical:
        _add_issue(
            audit,
            severity=AuditIssue.Severity.HIGH,
            category="technical",
            title="Missing canonical tags",
            why_it_matters="Canonical tags prevent duplicate-content dilution across URL variants.",
            affected_urls=missing_canonical,
            evidence=f"{len(missing_canonical)} pages have no rel=canonical.",
            recommendation="Add a self-referencing canonical on every indexable page.",
            estimated_effort="medium",
            origin="fact",
            confidence=1.0,
            priority=85,
        )
    if mixed:
        _add_issue(
            audit,
            severity=AuditIssue.Severity.HIGH,
            category="technical",
            title="Mixed content on HTTPS pages",
            why_it_matters="HTTP images or scripts on HTTPS pages are blocked by browsers and look untrustworthy.",
            affected_urls=list(dict.fromkeys(mixed))[:20],
            evidence=f"{len(mixed)} http:// resources were referenced from HTTPS pages.",
            recommendation="Serve every image, script, and stylesheet over HTTPS.",
            estimated_effort="medium",
            origin="fact",
            confidence=1.0,
            priority=88,
        )
    if redirect_heavy:
        _add_issue(
            audit,
            severity=AuditIssue.Severity.MEDIUM,
            category="technical",
            title="Redirect chains detected",
            why_it_matters="Chains slow crawlers and leak ranking signals.",
            affected_urls=redirect_heavy,
            evidence=f"{len(redirect_heavy)} URLs required two or more redirects.",
            recommendation="Point internal links at the final HTTPS URL so only one hop remains, if any.",
            estimated_effort="medium",
            origin="fact",
            confidence=1.0,
            priority=68,
        )
    if noindex and homepage.url in noindex:
        _add_issue(
            audit,
            severity=AuditIssue.Severity.CRITICAL,
            category="technical",
            title="Homepage is marked noindex",
            why_it_matters="noindex on the homepage removes the site from search and most AI citations.",
            affected_urls=[homepage.url],
            evidence="The homepage robots meta or X-Robots-Tag includes noindex.",
            recommendation="Remove noindex from the homepage unless this property is deliberately private.",
            estimated_effort="low",
            origin="fact",
            confidence=1.0,
            priority=99,
        )
    if missing_title:
        _add_issue(
            audit,
            severity=AuditIssue.Severity.HIGH,
            category="on_page",
            title="Missing title tags",
            why_it_matters="Title tags are a primary ranking and click-through signal.",
            affected_urls=missing_title,
            evidence=f"{len(missing_title)} crawled pages have no title element.",
            recommendation="Add a unique title of about 50–60 characters that names the page topic.",
            estimated_effort="low",
            origin="fact",
            confidence=1.0,
            priority=90,
        )
    if duplicate_titles:
        _add_issue(
            audit,
            severity=AuditIssue.Severity.MEDIUM,
            category="on_page",
            title="Duplicate title tags",
            why_it_matters="Repeated titles make it harder for crawlers to choose the right result.",
            affected_urls=_urls(pages, lambda page: page.title in duplicate_titles),
            evidence=f"{len(duplicate_titles)} title strings are reused across pages.",
            recommendation="Give every indexable URL a unique title.",
            estimated_effort="low",
            origin="fact",
            confidence=1.0,
            priority=74,
        )
    if short_title or long_title:
        _add_issue(
            audit,
            severity=AuditIssue.Severity.LOW,
            category="on_page",
            title="Title length outside the useful range",
            why_it_matters="Very short or very long titles are truncated or ignored in result snippets.",
            affected_urls=short_title + long_title,
            evidence=f"{len(short_title)} titles under 15 characters and {len(long_title)} over 65 characters.",
            recommendation="Rewrite titles to roughly 15–65 characters with the primary topic first.",
            estimated_effort="low",
            origin="fact",
            confidence=1.0,
            priority=55,
        )
    if missing_desc:
        _add_issue(
            audit,
            severity=AuditIssue.Severity.MEDIUM,
            category="on_page",
            title="Missing meta descriptions",
            why_it_matters="Search engines use descriptions in result snippets.",
            affected_urls=missing_desc,
            evidence=f"{len(missing_desc)} pages have no meta description.",
            recommendation="Write unique meta descriptions of 120–160 characters that match search intent.",
            estimated_effort="low",
            origin="fact",
            confidence=1.0,
            priority=70,
        )
    if short_desc:
        _add_issue(
            audit,
            severity=AuditIssue.Severity.LOW,
            category="on_page",
            title="Meta descriptions are too short",
            why_it_matters="Short snippets waste the click-through opportunity in search results.",
            affected_urls=short_desc,
            evidence=f"{len(short_desc)} descriptions are under 50 characters.",
            recommendation="Expand descriptions to a clear 120–160 character summary.",
            estimated_effort="low",
            origin="fact",
            confidence=1.0,
            priority=50,
        )
    if missing_og:
        _add_issue(
            audit,
            severity=AuditIssue.Severity.MEDIUM,
            category="on_page",
            title="Missing Open Graph tags",
            why_it_matters="Social and many AI crawlers use og:title and og:image when they cite a page.",
            affected_urls=missing_og,
            evidence=f"{len(missing_og)} pages have no og:title.",
            recommendation="Add og:title, og:description, and og:image on key templates.",
            estimated_effort="low",
            origin="fact",
            confidence=1.0,
            priority=62,
        )
    if missing_twitter:
        _add_issue(
            audit,
            severity=AuditIssue.Severity.LOW,
            category="on_page",
            title="Missing Twitter card tags",
            why_it_matters="Without twitter:card, shares fall back to a weak untitled preview.",
            affected_urls=missing_twitter,
            evidence=f"{len(missing_twitter)} pages have no twitter:card meta tag.",
            recommendation="Add twitter:card=summary_large_image and reuse the Open Graph image.",
            estimated_effort="low",
            origin="fact",
            confidence=1.0,
            priority=40,
        )
    if missing_h1:
        _add_issue(
            audit,
            severity=AuditIssue.Severity.MEDIUM,
            category="content",
            title="Missing H1 headings",
            why_it_matters="A single clear H1 helps humans and crawlers understand page topic.",
            affected_urls=missing_h1,
            evidence=f"{len(missing_h1)} pages have no H1.",
            recommendation="Add one descriptive H1 per page that matches the primary keyword.",
            estimated_effort="low",
            origin="fact",
            confidence=1.0,
            priority=65,
        )
    if multiple_h1:
        _add_issue(
            audit,
            severity=AuditIssue.Severity.LOW,
            category="content",
            title="Multiple H1 headings on a page",
            why_it_matters="Several H1s dilute the main topic for both users and answer engines.",
            affected_urls=multiple_h1,
            evidence=f"{len(multiple_h1)} pages have more than one H1.",
            recommendation="Keep a single H1 and use H2/H3 for supporting sections.",
            estimated_effort="low",
            origin="fact",
            confidence=1.0,
            priority=48,
        )
    if thin_pages:
        _add_issue(
            audit,
            severity=AuditIssue.Severity.MEDIUM,
            category="content",
            title="Thin content pages",
            why_it_matters="Pages with very little text rarely rank and are poor answers for AI overviews.",
            affected_urls=thin_pages,
            evidence=f"{len(thin_pages)} pages have fewer than 150 visible words.",
            recommendation="Expand useful pages with original explanations, FAQs, and evidence. Merge or noindex true stubs.",
            estimated_effort="high",
            origin="fact",
            confidence=1.0,
            priority=78,
        )
    if heading_skips:
        _add_issue(
            audit,
            severity=AuditIssue.Severity.LOW,
            category="content",
            title="Heading levels are skipped",
            why_it_matters="Broken heading order hurts accessibility and how answer engines outline a page.",
            affected_urls=heading_skips,
            evidence=f"{len(heading_skips)} pages jump heading levels (for example H1 then H3).",
            recommendation="Use H1 then H2 then H3 in order, without skipping levels.",
            estimated_effort="low",
            origin="fact",
            confidence=1.0,
            priority=42,
        )
    if keywords and not keyword_hits:
        _add_issue(
            audit,
            severity=AuditIssue.Severity.MEDIUM,
            category="content",
            title="Target keywords are missing from the homepage",
            why_it_matters="If the words customers search never appear, ranking and AI citation odds drop.",
            affected_urls=[homepage.url],
            evidence=f"None of the configured keywords ({', '.join(keywords[:8])}) appear in the homepage title, H1, or description.",
            recommendation="Place the primary keyword naturally in the title, H1, and opening paragraph.",
            estimated_effort="low",
            origin="fact",
            confidence=1.0,
            priority=76,
        )
    if not json_ld_pages:
        _add_issue(
            audit,
            severity=AuditIssue.Severity.HIGH,
            category="schema",
            title="No JSON-LD structured data detected",
            why_it_matters="Structured data is how search and answer engines understand entities, FAQs, and local businesses.",
            affected_urls=[homepage.url],
            evidence="No application/ld+json script was found on crawled pages.",
            recommendation="Add Organization and WebSite JSON-LD on the homepage. Add FAQPage or HowTo on relevant URLs.",
            estimated_effort="medium",
            origin="fact",
            confidence=1.0,
            priority=80,
        )
    elif not has_aeo_schema:
        _add_issue(
            audit,
            severity=AuditIssue.Severity.MEDIUM,
            category="aeo",
            title="Structured data is present but not answer-engine ready",
            why_it_matters="Generic JSON-LD without FAQ, HowTo, Article, or Organization is weakly used in AI overviews.",
            affected_urls=json_ld_pages[:8] or [homepage.url],
            evidence=f"Detected types: {', '.join(schema_types) or 'none'}. Missing FAQPage, HowTo, Article, WebSite, or Organization.",
            recommendation="Add FAQPage on Q&A content, HowTo on process pages, and Organization + WebSite on the homepage.",
            estimated_effort="medium",
            origin="fact",
            confidence=1.0,
            priority=73,
        )
    if not has_geo_schema and not hreflang and not market_hits:
        _add_issue(
            audit,
            severity=AuditIssue.Severity.MEDIUM,
            category="geo",
            title="No geographic targeting signals",
            why_it_matters="GEO (generative/geographic engine optimization) needs language, region, and place markup.",
            affected_urls=[homepage.url],
            evidence="No GeoCoordinates/Place schema, no hreflang, and target markets do not appear on the homepage.",
            recommendation="Set html lang, add hreflang if you serve multiple countries, and mark areaServed or geo on LocalBusiness schema.",
            estimated_effort="medium",
            origin="fact",
            confidence=1.0,
            priority=66,
        )
    if markets and not market_hits and not hreflang:
        _add_issue(
            audit,
            severity=AuditIssue.Severity.LOW,
            category="geo",
            title="Configured target markets are not visible on the homepage",
            why_it_matters="Markets you entered in SIPulse never appear in visible copy or hreflang.",
            affected_urls=[homepage.url],
            evidence=f"Target markets: {', '.join(markets[:8])}.",
            recommendation="Name the cities or countries you serve in the homepage copy and in LocalBusiness areaServed.",
            estimated_effort="low",
            origin="fact",
            confidence=1.0,
            priority=52,
        )
    if not nap:
        _add_issue(
            audit,
            severity=AuditIssue.Severity.MEDIUM,
            category="local",
            title="Name, address, or phone signals are weak",
            why_it_matters="Local pack and map visibility need a consistent NAP and LocalBusiness markup.",
            affected_urls=[homepage.url],
            evidence=f"Phones found: {len(phones)}. Emails: {len(emails)}. Address blocks: {len(addresses)}. LocalBusiness schema: {has_local_schema}.",
            recommendation="Publish a clickable tel: link, a postal address, and LocalBusiness JSON-LD that match Google Business Profile.",
            estimated_effort="medium",
            origin="fact",
            confidence=1.0,
            priority=71,
        )
    if alt_missing:
        _add_issue(
            audit,
            severity=AuditIssue.Severity.MEDIUM,
            category="accessibility",
            title="Images missing alt text",
            why_it_matters="Alt text is required for accessibility and useful for image search.",
            affected_urls=_urls(pages, lambda page: page.extracted.get("images_missing_alt")),
            evidence=f"{alt_missing} images are missing alt attributes.",
            recommendation="Add descriptive alt text to meaningful images. Use empty alt only for decorative images.",
            estimated_effort="medium",
            origin="fact",
            confidence=1.0,
            priority=60,
        )
    if missing_lang:
        _add_issue(
            audit,
            severity=AuditIssue.Severity.MEDIUM,
            category="accessibility",
            title="Missing html lang attribute",
            why_it_matters="Screen readers and language detectors need lang on the <html> element.",
            affected_urls=missing_lang,
            evidence=f"{len(missing_lang)} pages have no html lang.",
            recommendation="Set <html lang=\"en\"> (or the correct language code) on every template.",
            estimated_effort="low",
            origin="fact",
            confidence=1.0,
            priority=58,
        )
    if missing_viewport:
        _add_issue(
            audit,
            severity=AuditIssue.Severity.MEDIUM,
            category="accessibility",
            title="Missing mobile viewport tag",
            why_it_matters="Without a viewport meta tag, mobile users and Google mobile-first indexing see a desktop layout.",
            affected_urls=missing_viewport,
            evidence=f"{len(missing_viewport)} pages have no viewport meta tag.",
            recommendation="Add <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">.",
            estimated_effort="low",
            origin="fact",
            confidence=1.0,
            priority=64,
        )

    from apps.audits.performance import apply_performance_issues, build_performance_snapshot, enrich_performance_recommendations, score_page
    from apps.audits.performance_config import resolve_performance_config

    previous = (
        Audit.objects.filter(tenant=audit.tenant, website=website, status=Audit.Status.COMPLETED)
        .exclude(id=audit.id)
        .order_by("-completed_at", "-created_at")
        .first()
    )
    previous_snapshot = (previous.summary or {}).get("performance") if previous else None
    snapshot = build_performance_snapshot(pages, website=website, previous=previous_snapshot)
    apply_performance_issues(audit, snapshot)
    enrich_performance_recommendations(audit)
    cfg = resolve_performance_config(website)
    for page in pages:
        scored = score_page(page.extracted or {}, page.status_code, cfg)
        page.page_score = scored["score"]
        page.ttfb_ms = scored["ttfb_ms"]
        page.html_size_bytes = scored["html_bytes"]
        page.transfer_bytes = int((page.extracted or {}).get("transfer_bytes") or scored["html_bytes"])
        page.compression = str((page.extracted or {}).get("compression") or "")[:20]
        page.http_protocol = str((page.extracted or {}).get("http_protocol") or "")[:20]
        page.save(update_fields=["page_score", "ttfb_ms", "html_size_bytes", "transfer_bytes", "compression", "http_protocol", "updated_at"])

    issue_count = audit.issues.count()
    avg_ttfb = int((snapshot.get("kpis") or {}).get("avg_ttfb_ms") or 0)

    technical = 100
    technical -= 25 if not https_ok else 0
    technical -= 12 if not robots_found else 0
    technical -= 14 if not sitemap_found else 0
    technical -= min(24, len(missing_canonical) * 6)
    technical -= min(16, len(error_pages) * 8)
    technical -= 10 if mixed else 0
    technical -= 8 if redirect_heavy else 0
    technical -= 20 if homepage.url in noindex else 0
    technical -= 0 if hsts else 4

    on_page = 100
    on_page -= min(30, len(missing_title) * 8)
    on_page -= min(18, len(missing_desc) * 5)
    on_page -= min(12, len(duplicate_titles) * 6)
    on_page -= min(10, len(missing_og) * 3)
    on_page -= min(6, len(short_title + long_title + short_desc) * 2)

    content = 100
    content -= min(28, len(missing_h1) * 7)
    content -= min(24, len(thin_pages) * 8)
    content -= min(8, len(multiple_h1) * 3)
    content -= 12 if keywords and not keyword_hits else 0

    schema = 85 if json_ld_pages else 32
    if json_ld_pages and has_aeo_schema:
        schema = min(100, schema + 10)
    if has_local_schema:
        schema = min(100, schema + 5)

    accessibility = 100
    accessibility -= min(35, alt_missing * 2)
    accessibility -= min(12, len(missing_lang) * 4)
    accessibility -= min(12, len(missing_viewport) * 4)

    aeo = 38
    if json_ld_pages:
        aeo += 18
    if has_aeo_schema:
        aeo += 22
    if "FAQPage" in schema_types or "QAPage" in schema_types:
        aeo += 12
    if "HowTo" in schema_types:
        aeo += 8
    if not thin_pages:
        aeo += 8
    if missing_h1:
        aeo -= min(10, len(missing_h1) * 2)

    geo = 40
    if homepage.extracted.get("html_lang"):
        geo += 12
    if hreflang:
        geo += 16
    if has_geo_schema:
        geo += 18
    if market_hits:
        geo += 12
    if markets and not market_hits:
        geo -= 8

    local_seo = 42
    if phones:
        local_seo += 14
    if addresses:
        local_seo += 14
    if has_local_schema:
        local_seo += 18
    if nap:
        local_seo += 8
    if emails and not phones:
        local_seo += 4

    performance = int(snapshot.get("overall_score") or 0)
    technical_performance = int(snapshot.get("technical_score") or performance)
    ux_cwv = snapshot.get("ux_score")

    scores = {
        "technical_seo": _clamp(technical),
        "on_page_seo": _clamp(on_page),
        "content": _clamp(content),
        "schema": _clamp(schema),
        "accessibility": _clamp(accessibility),
        "aeo": _clamp(aeo),
        "geo": _clamp(geo),
        "performance": _clamp(performance),
        "technical_performance": _clamp(technical_performance),
        "local_seo": _clamp(local_seo),
    }
    if ux_cwv is not None:
        scores["ux_cwv"] = _clamp(ux_cwv)
    overall = _clamp(
        (
            scores["technical_seo"] * 1.2
            + scores["on_page_seo"] * 1.1
            + scores["content"]
            + scores["aeo"]
            + scores["geo"]
            + scores["schema"]
            + scores["accessibility"]
            + scores["performance"] * 0.8
            + scores["local_seo"] * 0.8
        )
        / 8.9
    )
    opportunity = _clamp(100 - min(45, issue_count * 3) - (8 if any(item.severity == "critical" for item in audit.issues.all()) else 0))
    scores["opportunity"] = opportunity

    previous_overall = previous.overall_score if previous else None
    delta = None if previous_overall is None else overall - int(previous_overall)

    audit.scores = scores
    audit.overall_score = overall
    audit.issue_count = issue_count
    audit.summary = {
        "https": https_ok,
        "hsts": hsts,
        "robots_txt": robots_found,
        "sitemap": sitemap_found,
        "sitemap_urls": sitemap.get("url_count") or 0,
        "schema_types": schema_types,
        "avg_ttfb_ms": avg_ttfb,
        "median_ttfb_ms": (snapshot.get("kpis") or {}).get("median_ttfb_ms"),
        "thin_pages": len(thin_pages),
        "faq_schema": "FAQPage" in schema_types or "QAPage" in schema_types,
        "local_business": has_local_schema,
        "nap": {"phones": phones[:6], "emails": emails[:6], "addresses": addresses[:3]},
        "keyword_hits": keyword_hits,
        "market_hits": market_hits,
        "hreflang": list(dict.fromkeys(hreflang))[:12],
        "previous_overall": previous_overall,
        "delta": delta,
        "performance_note": snapshot.get("explain", {}).get("overall")
        or "SIPulse Performance Score is crawl-measured (TTFB, HTML size, redirects, compression, caching, protocol). Lighthouse is optional lab overlay, never the sole score.",
        "performance": snapshot,
        "competitors": list(website.competitors or [])[:12],
        "open_critical": audit.issues.filter(severity=AuditIssue.Severity.CRITICAL).count(),
        "open_high": audit.issues.filter(severity=AuditIssue.Severity.HIGH).count(),
    }
    signals = dict(crawl.signals or {})
    signals["performance"] = snapshot
    crawl.signals = signals
    crawl.save(update_fields=["signals", "updated_at"])
    audit.status = Audit.Status.COMPLETED
    audit.completed_at = timezone.now()
    audit.save()
    return audit
