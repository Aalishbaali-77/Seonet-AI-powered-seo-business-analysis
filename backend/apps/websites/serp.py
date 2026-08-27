from __future__ import annotations

import os
from urllib.parse import urlparse

import httpx

from apps.common.exceptions import APIError
from apps.platform.lead_sources import resolve_source_credentials
from providers.ai.base import ProviderUnavailable

GOOGLE_CSE_URL = "https://www.googleapis.com/customsearch/v1"
SERPAPI_URL = "https://serpapi.com/search.json"


def _cse_id(raw: str) -> str:
    value = (raw or "").strip()
    if not value:
        return ""
    if "cx=" in value:
        return value.split("cx=", 1)[1].split("&", 1)[0].strip()
    if value.startswith("http://") or value.startswith("https://"):
        return ""
    return value


def _host_matches(domain: str, result_host: str) -> bool:
    site = (domain or "").lower().removeprefix("www.")
    found = (result_host or "").lower().removeprefix("www.")
    if not site or not found:
        return False
    return found == site or found.endswith("." + site)


def resolve_serp_provider() -> tuple[str, str, str]:
    source, key = resolve_source_credentials("google_custom_search")
    cx = ""
    if source is not None:
        public = source.public_config or {}
        cx = _cse_id(str(public.get("search_engine_id") or public.get("search_url") or ""))
    if not cx:
        cx = _cse_id(os.getenv("GOOGLE_CSE_ID") or os.getenv("GOOGLE_CSE_CX") or "")
    if key and cx:
        return "google_custom_search", key, cx
    source, key = resolve_source_credentials("serpapi")
    if key:
        return "serpapi", key, ""
    return "", "", ""


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


def search_official_website(query: str) -> str:
    provider, api_key, cx = resolve_serp_provider()
    if not provider or not query.strip():
        return ""
    try:
        if provider == "google_custom_search":
            rows = _google_cse(query[:180], api_key, cx)
        else:
            rows = _serpapi(query[:180], api_key)
    except (APIError, ProviderUnavailable):
        return ""
    for item in rows:
        host = item.get("host") or ""
        if not host or any(host == blocked or host.endswith("." + blocked) for blocked in DIRECTORY_HOSTS):
            continue
        return item.get("url") or ""
    return ""


def lookup_keyword(*, query: str, domain: str, provider: str, api_key: str, cx: str = "") -> dict:
    if provider == "google_custom_search":
        rows = _google_cse(query, api_key, cx)
    elif provider == "serpapi":
        rows = _serpapi(query, api_key)
    else:
        raise APIError("No licensed search provider is enabled.", code="VALIDATION_ERROR")
    match = next((item for item in rows if _host_matches(domain, item["host"])), None)
    return {
        "keyword": query,
        "position": match["position"] if match else None,
        "in_first_page": bool(match and match["position"] and match["position"] <= 10),
        "matched_url": match["url"] if match else "",
        "matched_title": match["title"] if match else "",
        "sample_size": len(rows),
        "origin": "fact",
        "source": provider,
    }


def probe_serp(provider: str, api_key: str, cx: str = "") -> dict:
    if provider == "google_custom_search":
        if not cx:
            raise APIError("Store the Programmable Search Engine ID in Licensed search URL.", code="VALIDATION_ERROR")
        _google_cse("example", api_key, cx)
        return {"ok": True, "provider": provider, "message": "Google Custom Search accepted the key and engine ID."}
    if provider == "serpapi":
        _serpapi("example", api_key)
        return {"ok": True, "provider": provider, "message": "SerpAPI accepted the key."}
    raise APIError("This source cannot be tested yet.", code="VALIDATION_ERROR")


def _google_cse(query: str, api_key: str, cx: str) -> list[dict]:
    try:
        with httpx.Client(timeout=25, follow_redirects=True) as client:
            response = client.get(GOOGLE_CSE_URL, params={"key": api_key, "cx": cx, "q": query[:180], "num": 10})
    except httpx.HTTPError as exc:
        raise ProviderUnavailable("Google Custom Search is unavailable.") from exc
    if response.status_code == 403:
        raise APIError("Google Custom Search rejected the key or engine ID.", code="VALIDATION_ERROR")
    if response.status_code >= 400:
        raise ProviderUnavailable(f"Google Custom Search returned HTTP {response.status_code}.")
    data = response.json() if response.content else {}
    return [_row(index + 1, item.get("link") or "", item.get("title") or "") for index, item in enumerate(data.get("items") or [])]


def _serpapi(query: str, api_key: str) -> list[dict]:
    try:
        with httpx.Client(timeout=25, follow_redirects=True) as client:
            response = client.get(SERPAPI_URL, params={"engine": "google", "q": query[:180], "api_key": api_key, "num": 10})
    except httpx.HTTPError as exc:
        raise ProviderUnavailable("SerpAPI is unavailable.") from exc
    if response.status_code == 401:
        raise APIError("SerpAPI rejected the key.", code="VALIDATION_ERROR")
    if response.status_code >= 400:
        raise ProviderUnavailable(f"SerpAPI returned HTTP {response.status_code}.")
    data = response.json() if response.content else {}
    if data.get("error"):
        raise ProviderUnavailable(str(data.get("error")))
    rows = []
    for item in data.get("organic_results") or []:
        position = int(item.get("position") or 0) or None
        rows.append(_row(position or len(rows) + 1, item.get("link") or "", item.get("title") or ""))
    return rows[:10]


def _row(position: int, url: str, title: str) -> dict:
    host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    return {"position": position, "url": url, "title": title, "host": host}
