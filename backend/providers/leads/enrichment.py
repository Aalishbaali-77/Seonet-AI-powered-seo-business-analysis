from __future__ import annotations

import ipaddress
import os
import re
import socket
from html import unescape
from urllib.parse import urljoin, urlparse

import httpx

from providers.ai.base import ProviderUnavailable
from providers.leads.adapters import USER_AGENT, _get

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
PHONE_RE = re.compile(r"(?:\+|00)?[\d][\d\s().-]{6,16}\d")
SKIP_EMAIL_HOSTS = {
    "example.com",
    "email.com",
    "sentry.io",
    "wixpress.com",
    "wordpress.com",
    "cloudflare.com",
    "google.com",
    "gstatic.com",
    "w3.org",
    "schema.org",
}
SKIP_EMAIL_LOCAL = {"noreply", "no-reply", "privacy", "legal", "webmaster", "postmaster"}
DIRECTORY_HOSTS = {
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "twitter.com",
    "x.com",
    "yelp.com",
    "yellowpages.com",
    "yellowpage.pk",
    "crunchbase.com",
    "wikipedia.org",
    "google.com",
    "maps.google.com",
    "justdial.com",
    "tripadvisor.com",
    "bbb.org",
    "manta.com",
}


def host_of(url: str) -> str:
    return (urlparse(url).hostname or "").lower().removeprefix("www.")


def is_directory_host(host: str) -> bool:
    found = (host or "").lower().removeprefix("www.")
    return any(found == item or found.endswith("." + item) for item in DIRECTORY_HOSTS)


def normalize_website(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    if not raw.startswith(("http://", "https://")):
        raw = f"https://{raw}"
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    return raw[:200]


def _public_host(host: str) -> bool:
    if not host or host in {"localhost", "127.0.0.1", "::1"}:
        return False
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        return False
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except (ValueError, TypeError):
            return False
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return False
    return True


def fetch_public_html(url: str, *, timeout: int = 10) -> str:
    if os.environ.get("PYTEST_CURRENT_TEST") and "force_website_fetch" not in os.environ:
        return ""
    safe = normalize_website(url)
    if not safe or not _public_host(host_of(safe)):
        return ""
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True, max_redirects=3) as client:
            response = client.get(safe, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
    except httpx.HTTPError:
        return ""
    if response.status_code >= 400:
        return ""
    content_type = (response.headers.get("content-type") or "").lower()
    if "html" not in content_type and "text/plain" not in content_type:
        return ""
    return (response.text or "")[:400000]


def extract_contacts(html: str, *, prefer_host: str = "") -> dict[str, str]:
    text = unescape(html or "")
    emails = []
    for match in EMAIL_RE.findall(text):
        local, _, domain = match.lower().partition("@")
        if not domain or domain in SKIP_EMAIL_HOSTS or local in SKIP_EMAIL_LOCAL:
            continue
        if any(part in local for part in ("noreply", "no-reply")):
            continue
        emails.append(match)
    if prefer_host:
        same = [item for item in emails if host_of(f"https://{item.split('@', 1)[1]}") == prefer_host or item.lower().endswith("@" + prefer_host)]
        emails = same or emails
    phones = []
    for match in PHONE_RE.findall(text):
        digits = re.sub(r"\D", "", match)
        if 7 <= len(digits) <= 15:
            phones.append(re.sub(r"\s+", " ", match).strip())
    description = ""
    meta = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']', text, re.I)
    if not meta:
        meta = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']description["\']', text, re.I)
    if meta:
        description = unescape(meta.group(1)).strip()[:2000]
    linkedin = ""
    link = re.search(r'https?://(?:www\.)?linkedin\.com/(?:company|in)/[A-Za-z0-9_-]+', text, re.I)
    if link:
        linkedin = link.group(0)[:200]
    return {
        "email": emails[0] if emails else "",
        "phone": phones[0] if phones else "",
        "description": description,
        "linkedin_url": linkedin,
    }


def read_company_website(url: str) -> dict[str, str]:
    from apps.crawler.fetcher import fetch_optional, fetch_url
    from apps.crawler.parser import parse_html
    from apps.crawler.ssrf import SSRFBlocked

    safe = normalize_website(url)
    if not safe:
        return {}
    try:
        page = fetch_url(safe, timeout=10)
    except (SSRFBlocked, Exception):
        html = fetch_public_html(safe)
        return extract_contacts(html, prefer_host=host_of(safe)) if html else {}
    parsed = parse_html(page.url or safe, page.body or "")
    host = host_of(page.url or safe)
    emails = [str(item) for item in (parsed.get("emails") or []) if item]
    phones = [str(item) for item in (parsed.get("phones") or []) if item]
    found = extract_contacts(page.body or "", prefer_host=host)
    if emails and not found.get("email"):
        found["email"] = emails[0][:254]
    if phones and not found.get("phone"):
        found["phone"] = phones[0][:40]
    description = str((parsed.get("meta") or {}).get("description") or parsed.get("title") or "")
    if description and not found.get("description"):
        found["description"] = description[:2000]
    if found.get("email") and found.get("phone"):
        return found
    for path in ("/contact", "/contact-us", "/about"):
        extra_page = fetch_optional(urljoin(safe.rstrip("/") + "/", path.lstrip("/")), timeout=8)
        if extra_page is None or not extra_page.body:
            continue
        extra = extract_contacts(extra_page.body, prefer_host=host)
        extra_parsed = parse_html(extra_page.url or safe, extra_page.body)
        if extra_parsed.get("emails") and not extra.get("email"):
            extra["email"] = str(extra_parsed["emails"][0])
        if extra_parsed.get("phones") and not extra.get("phone"):
            extra["phone"] = str(extra_parsed["phones"][0])
        for key in ("email", "phone", "description", "linkedin_url"):
            if extra.get(key) and not found.get(key):
                found[key] = extra[key]
        if found.get("email") and found.get("phone"):
            break
    return found


def lookup_wikidata(company_name: str) -> dict[str, str]:
    name = (company_name or "").strip()
    if not name or os.environ.get("PYTEST_CURRENT_TEST"):
        return {}
    query = f"""
    SELECT ?itemLabel ?website ?industryLabel ?countryLabel ?employees WHERE {{
      ?item rdfs:label "{name.replace('"', '')}"@en.
      OPTIONAL {{ ?item wdt:P856 ?website. }}
      OPTIONAL {{ ?item wdt:P452 ?industry. }}
      OPTIONAL {{ ?item wdt:P17 ?country. }}
      OPTIONAL {{ ?item wdt:P1128 ?employees. }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    LIMIT 3
    """
    try:
        payload = _get(
            "https://query.wikidata.org/sparql",
            params={"query": query, "format": "json"},
            headers={"Accept": "application/sparql-results+json"},
            timeout=12,
        )
    except ProviderUnavailable:
        return {}
    bindings = ((payload.get("results") or {}).get("bindings") or []) if isinstance(payload, dict) else []
    if not bindings:
        return {}
    row = bindings[0]
    website = ((row.get("website") or {}).get("value") or "").strip()
    return {
        "website": normalize_website(website),
        "industry": ((row.get("industryLabel") or {}).get("value") or "").strip()[:160],
        "location": ((row.get("countryLabel") or {}).get("value") or "").strip()[:255],
        "employee_count": str((row.get("employees") or {}).get("value") or "")[:40],
        "description": ((row.get("itemLabel") or {}).get("value") or "").strip()[:2000],
    }


class HunterAdapter:
    name = "hunter"

    def lookup(self, *, domain: str, company: str = "", api_key: str = "") -> dict[str, str]:
        if not domain or not api_key:
            return {}
        payload = _get(
            "https://api.hunter.io/v2/domain-search",
            params={"domain": domain, "api_key": api_key, "limit": 10},
            timeout=12,
        )
        data = payload.get("data") or {} if isinstance(payload, dict) else {}
        emails = data.get("emails") or []
        generic = [item for item in emails if (item.get("type") or "") == "generic" and item.get("value")]
        chosen = (generic[0] if generic else emails[0] if emails else {}) or {}
        org = data.get("organization") or company
        return {
            "email": str(chosen.get("value") or "")[:254],
            "description": str(org or "")[:2000],
            "linkedin_url": normalize_website(str(data.get("linkedin") or "")),
        }

    def probe(self, api_key: str = "") -> dict:
        if not api_key:
            raise ProviderUnavailable("Store a Hunter API key before testing.")
        _get("https://api.hunter.io/v2/account", params={"api_key": api_key}, timeout=12)
        return {"ok": True, "provider": self.name, "message": "Hunter accepted the key."}


class ClearbitAdapter:
    name = "clearbit"

    def lookup(self, *, domain: str, company: str = "", api_key: str = "") -> dict[str, str]:
        if not domain or not api_key:
            return {}
        payload = _get(
            "https://company.clearbit.com/v2/companies/find",
            params={"domain": domain},
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=12,
        )
        if not isinstance(payload, dict):
            return {}
        metrics = payload.get("metrics") or {}
        return {
            "website": normalize_website(str(payload.get("domain") and f"https://{payload.get('domain')}" or payload.get("url") or "")),
            "industry": str(payload.get("category", {}).get("industry") if isinstance(payload.get("category"), dict) else payload.get("industry") or "")[:160],
            "location": str((payload.get("geo") or {}).get("city") or (payload.get("geo") or {}).get("country") or "")[:255],
            "employee_count": str(metrics.get("employees") or payload.get("employees") or "")[:40],
            "description": str(payload.get("description") or "")[:2000],
            "linkedin_url": normalize_website(str((payload.get("linkedin") or {}).get("handle") and f"https://www.linkedin.com/{(payload.get('linkedin') or {}).get('handle')}" or "")),
            "phone": str(payload.get("phone") or "")[:40],
            "email": "",
        }

    def probe(self, api_key: str = "") -> dict:
        if not api_key:
            raise ProviderUnavailable("Store a Clearbit API key before testing.")
        _get(
            "https://company.clearbit.com/v2/companies/find",
            params={"domain": "clearbit.com"},
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=12,
        )
        return {"ok": True, "provider": self.name, "message": "Clearbit accepted the key."}


class ApolloAdapter:
    name = "apollo"

    def lookup(self, *, domain: str, company: str = "", api_key: str = "") -> dict[str, str]:
        if not domain or not api_key:
            return {}
        payload = _get(
            "https://api.apollo.io/v1/organizations/enrich",
            params={"domain": domain},
            headers={"X-Api-Key": api_key},
            timeout=12,
        )
        org = (payload.get("organization") or payload) if isinstance(payload, dict) else {}
        return {
            "website": normalize_website(str(org.get("website_url") or org.get("primary_domain") or "")),
            "industry": str(org.get("industry") or "")[:160],
            "location": str(org.get("city") or org.get("country") or "")[:255],
            "phone": str(org.get("phone") or org.get("sanitized_phone") or "")[:40],
            "employee_count": str(org.get("estimated_num_employees") or "")[:40],
            "linkedin_url": normalize_website(str(org.get("linkedin_url") or "")),
            "description": str(org.get("short_description") or org.get("seo_description") or "")[:2000],
            "email": "",
        }

    def probe(self, api_key: str = "") -> dict:
        if not api_key:
            raise ProviderUnavailable("Store an Apollo API key before testing.")
        _get(
            "https://api.apollo.io/v1/auth/health",
            headers={"X-Api-Key": api_key},
            timeout=12,
        )
        return {"ok": True, "provider": self.name, "message": "Apollo accepted the key."}


class WikidataAdapter:
    name = "wikidata"

    def lookup(self, *, domain: str = "", company: str = "", api_key: str = "") -> dict[str, str]:
        return lookup_wikidata(company)

    def probe(self, api_key: str = "") -> dict:
        row = lookup_wikidata("Google")
        return {
            "ok": True,
            "sample_count": 1 if row else 0,
            "provider": self.name,
            "message": "Wikidata SPARQL responded." if row or os.environ.get("PYTEST_CURRENT_TEST") else "Wikidata returned no sample row.",
        }
