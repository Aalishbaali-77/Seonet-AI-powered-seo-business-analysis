from __future__ import annotations

from html import escape
from urllib.parse import urljoin, urlparse

from apps.audits.models import AuditIssue

TITLE_TO_FIX = {
    "robots.txt was not found": "robots_txt",
    "XML sitemap was not found": "sitemap_xml",
    "Missing canonical tags": "canonical",
    "Missing title tags": "title",
    "Title length outside the useful range": "title",
    "Missing meta descriptions": "meta_description",
    "Meta descriptions are too short": "meta_description",
    "Missing Open Graph tags": "open_graph",
    "Missing Twitter card tags": "twitter",
    "No JSON-LD structured data detected": "json_ld",
    "Structured data is present but not answer-engine ready": "json_ld",
    "No geographic targeting signals": "json_ld",
    "Configured target markets are not visible on the homepage": "json_ld",
    "Missing html lang attribute": "html_lang",
    "Missing mobile viewport tag": "viewport",
    "Homepage is marked noindex": "remove_noindex",
}

FILE_FIXES = {
    "robots_txt",
    "sitemap_xml",
    "canonical",
    "title",
    "meta_description",
    "open_graph",
    "twitter",
    "json_ld",
    "html_lang",
    "viewport",
    "remove_noindex",
}

WORDPRESS_FIXES = {"title", "meta_description"}
HOMEPAGE_FILES = ("index.html", "home.html", "default.html")


def plan_fixes(*, website, audit, can_write_files: bool, wordpress: bool) -> dict:
    applicable = []
    skipped = []
    seen = set()
    for issue in audit.issues.all().order_by("priority"):
        code = TITLE_TO_FIX.get(issue.title)
        if not code:
            skipped.append(_skip(issue, "Not an allowlisted auto-fix. Change this on the server or in the CMS."))
            continue
        if code in seen:
            continue
        if code in WORDPRESS_FIXES and wordpress:
            seen.add(code)
            applicable.append(_item(issue, code, "wordpress"))
            continue
        if code in FILE_FIXES and can_write_files:
            seen.add(code)
            applicable.append(_item(issue, code, "file"))
            continue
        if code in FILE_FIXES and not can_write_files:
            skipped.append(_skip(issue, "Needs FTP, SFTP, or cPanel file access. A WordPress application password cannot write these files."))
            continue
        skipped.append(_skip(issue, "This recommendation is not applied automatically."))
    return {
        "applicable": applicable,
        "skipped": skipped,
        "why": "Only allowlisted on-page and crawl files are applied. Performance, HTTPS, and invented copy are never written.",
    }


def apply_planned_fixes(*, website, audit, transport, plan: dict | None = None) -> dict:
    planned = plan or plan_fixes(
        website=website,
        audit=audit,
        can_write_files=transport.can_write_files(),
        wordpress=transport.kind == "wordpress",
    )
    applied = []
    skipped = list(planned.get("skipped") or [])
    errors = []
    origin = urlparse(website.url)
    base = f"{origin.scheme}://{origin.netloc}"
    title = website.name or website.business_name or website.domain
    description = (website.description or "").strip() or f"{title} website."
    if transport.kind == "wordpress":
        wp_codes = {item["code"] for item in planned.get("applicable") or [] if item.get("via") == "wordpress"}
        if wp_codes & WORDPRESS_FIXES:
            try:
                transport.update_wordpress_settings(title=title, description=description)
                for item in planned.get("applicable") or []:
                    if item.get("via") == "wordpress":
                        applied.append({**item, "status": "applied"})
            except Exception as exc:  # noqa: BLE001
                errors.append(str(exc)[:400])
                skipped.extend({**item, "reason": str(exc)[:240]} for item in planned.get("applicable") or [] if item.get("via") == "wordpress")
    file_items = [item for item in planned.get("applicable") or [] if item.get("via") == "file"]
    if file_items and transport.can_write_files():
        try:
            _apply_files(transport, website=website, audit=audit, base=base, title=title, description=description, codes={item["code"] for item in file_items})
            applied.extend({**item, "status": "applied"} for item in file_items)
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc)[:400])
            skipped.extend({**item, "reason": str(exc)[:240]} for item in file_items)
    elif file_items:
        skipped.extend({**item, "reason": "File access is not available on this connection."} for item in file_items)
    return {"applied": applied, "skipped": skipped, "errors": errors[:8], "plan_why": planned.get("why") or ""}


def _apply_files(transport, *, website, audit, base: str, title: str, description: str, codes: set[str]) -> None:
    if "robots_txt" in codes:
        transport.write_file("robots.txt", _robots(base).encode("utf-8"))
    if "sitemap_xml" in codes:
        urls = [page.url for page in (audit.crawl.pages.all() if audit.crawl_id else []) if page.url]
        if website.url not in urls:
            urls = [website.url, *urls]
        transport.write_file("sitemap.xml", _sitemap(urls[:80]).encode("utf-8"))
    html_codes = codes - {"robots_txt", "sitemap_xml"}
    if not html_codes:
        return
    target = _homepage_name(transport)
    if not target:
        raise RuntimeError("No index.html (or home.html) in the document root. PHP themes were not patched.")
    raw = transport.read_file(target) or b""
    html = raw.decode("utf-8", errors="ignore")
    html = _patch_html(
        html,
        website=website,
        base=base,
        title=title,
        description=description,
        codes=html_codes,
    )
    transport.write_file(target, html.encode("utf-8"))


def _homepage_name(transport) -> str | None:
    names = {name.lower(): name for name in transport.list_names()}
    for candidate in HOMEPAGE_FILES:
        if candidate in names:
            return names[candidate]
    return None


def _patch_html(html: str, *, website, base: str, title: str, description: str, codes: set[str]) -> str:
    text = html or "<!doctype html><html><head></head><body></body></html>"
    if "<head" not in text.lower():
        text = text.replace("<html", "<html><head></head", 1) if "<html" in text.lower() else f"<html><head></head>{text}</html>"
    if "html_lang" in codes and "lang=" not in text.lower():
        text = text.replace("<html", '<html lang="en"', 1)
    if "remove_noindex" in codes:
        text = text.replace('content="noindex,follow"', "").replace('content="noindex"', "").replace("noindex,follow", "").replace("noindex", "")
    inject = []
    if "title" in codes and "<title" not in text.lower():
        inject.append(f"<title>{escape(title)[:70]}</title>")
    if "meta_description" in codes and 'name="description"' not in text.lower():
        inject.append(f'<meta name="description" content="{escape(description)[:160]}" />')
    if "viewport" in codes and "viewport" not in text.lower():
        inject.append('<meta name="viewport" content="width=device-width, initial-scale=1" />')
    if "canonical" in codes and 'rel="canonical"' not in text.lower():
        inject.append(f'<link rel="canonical" href="{escape(urljoin(base, "/"))}" />')
    if "open_graph" in codes and "og:title" not in text.lower():
        inject.extend(
            [
                f'<meta property="og:title" content="{escape(title)[:70]}" />',
                f'<meta property="og:description" content="{escape(description)[:160]}" />',
                f'<meta property="og:url" content="{escape(urljoin(base, "/"))}" />',
            ]
        )
    if "twitter" in codes and "twitter:card" not in text.lower():
        inject.append('<meta name="twitter:card" content="summary" />')
        inject.append(f'<meta name="twitter:title" content="{escape(title)[:70]}" />')
    if "json_ld" in codes and "application/ld+json" not in text.lower():
        inject.append(_json_ld(website, base, title, description))
    if inject:
        snippet = "\n".join(inject) + "\n"
        lowered = text.lower()
        idx = lowered.find("</head>")
        if idx >= 0:
            text = text[:idx] + snippet + text[idx:]
        else:
            text = snippet + text
    return text


def _json_ld(website, base: str, title: str, description: str) -> str:
    markets = [str(item) for item in (website.target_markets or []) if item][:8]
    payload = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "WebSite", "name": title, "url": urljoin(base, "/"), "description": description},
            {
                "@type": "Organization",
                "name": website.business_name or title,
                "url": urljoin(base, "/"),
                **({"areaServed": markets} if markets else {}),
            },
        ],
    }
    import json

    return f'<script type="application/ld+json">{json.dumps(payload, ensure_ascii=True)}</script>'


def _robots(base: str) -> str:
    return f"User-agent: *\nAllow: /\nSitemap: {urljoin(base, '/sitemap.xml')}\n"


def _sitemap(urls: list[str]) -> str:
    rows = "\n".join(f"  <url><loc>{escape(url)}</loc></url>" for url in urls if url.startswith("http"))
    return '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + rows + "\n</urlset>\n"


def _item(issue: AuditIssue, code: str, via: str) -> dict:
    return {"issue_id": str(issue.id), "title": issue.title, "code": code, "via": via, "category": issue.category}


def _skip(issue: AuditIssue, reason: str) -> dict:
    return {"issue_id": str(issue.id), "title": issue.title, "reason": reason, "category": issue.category}
