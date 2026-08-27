from __future__ import annotations

from typing import Any

import httpx

from providers.ai.base import ProviderUnavailable

USER_AGENT = "SIPulseBot/1.0 (+https://sipulse.local)"


def _get(url: str, *, params: dict | None = None, headers: dict | None = None, timeout: int = 20) -> dict | list:
    merged = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    merged.update(headers or {})
    with httpx.Client(timeout=timeout, follow_redirects=False) as client:
        response = client.get(url, params=params, headers=merged)
    if response.status_code >= 400:
        detail = ""
        try:
            payload = response.json()
            detail = str(payload.get("error") or payload.get("message") or payload.get("error_description") or "")[:300]
        except Exception:  # noqa: BLE001
            detail = (response.text or "")[:200]
        raise ProviderUnavailable(f"{url} returned HTTP {response.status_code}. {detail}".strip())
    try:
        return response.json()
    except Exception as exc:  # noqa: BLE001
        raise ProviderUnavailable("Provider returned a non-JSON response.") from exc


def _split_location(text: str) -> tuple[str, str]:
    lowered = text.lower()
    if " in " not in lowered:
        return text.strip(), ""
    index = lowered.rfind(" in ")
    return text[:index].strip(), text[index + 4 :].strip()


def _record(
    *,
    source: str,
    source_id: str,
    name: str,
    location: str = "",
    website: str = "",
    industry: str = "",
    phone: str = "",
    email: str = "",
) -> dict[str, Any]:
    return {
        "source": source,
        "source_record_id": str(source_id or name)[:120],
        "company_name": (name or "Unknown")[:255],
        "location": (location or "")[:255],
        "website": (website or "")[:200],
        "industry": (industry or "")[:160],
        "phone": (phone or "")[:40],
        "email": (email or "")[:254],
    }


class YelpAdapter:
    name = "yelp"
    SEARCH_URL = "https://api.yelp.com/v3/businesses/search"

    def search(self, *, query: dict[str, Any], api_key: str = "", limit: int = 20) -> list[dict[str, Any]]:
        text = str(query.get("text") or "").strip()
        if not text or not api_key:
            return []
        term, location = _split_location(text)
        payload = _get(
            self.SEARCH_URL,
            params={"term": term or text, "location": location or text, "limit": min(limit, 20)},
            headers={"Authorization": f"Bearer {api_key}"},
        )
        records = []
        for item in (payload.get("businesses") or [])[:limit]:
            address = ", ".join((item.get("location") or {}).get("display_address") or [])
            categories = item.get("categories") or []
            industry = str((categories[0] or {}).get("title") or "") if categories else ""
            records.append(
                _record(
                    source=self.name,
                    source_id=item.get("id") or item.get("alias") or item.get("name"),
                    name=item.get("name") or "Unknown",
                    location=address,
                    website=item.get("url") or "",
                    industry=industry,
                    phone=item.get("display_phone") or item.get("phone") or "",
                )
            )
        return records

    def probe(self, api_key: str = "") -> dict[str, Any]:
        rows = self.search(query={"text": "restaurants in New York"}, api_key=api_key, limit=3)
        return {"ok": True, "sample_count": len(rows), "provider": self.name, "message": f"Yelp Fusion returned {len(rows)} sample businesses."}


class FoursquareAdapter:
    name = "foursquare"
    SEARCH_URL = "https://api.foursquare.com/v3/places/search"

    def search(self, *, query: dict[str, Any], api_key: str = "", limit: int = 20) -> list[dict[str, Any]]:
        text = str(query.get("text") or "").strip()
        if not text or not api_key:
            return []
        term, near = _split_location(text)
        params: dict[str, Any] = {"query": term or text, "limit": min(limit, 20)}
        if near:
            params["near"] = near
        payload = _get(self.SEARCH_URL, params=params, headers={"Authorization": api_key})
        records = []
        for item in (payload.get("results") or [])[:limit]:
            loc = item.get("location") or {}
            categories = item.get("categories") or []
            industry = str((categories[0] or {}).get("name") or "") if categories else ""
            records.append(
                _record(
                    source=self.name,
                    source_id=item.get("fsq_id") or item.get("name"),
                    name=item.get("name") or "Unknown",
                    location=loc.get("formatted_address") or loc.get("address") or "",
                    website=(item.get("website") or ""),
                    industry=industry,
                    phone=item.get("tel") or "",
                )
            )
        return records

    def probe(self, api_key: str = "") -> dict[str, Any]:
        rows = self.search(query={"text": "coffee in New York"}, api_key=api_key, limit=3)
        return {"ok": True, "sample_count": len(rows), "provider": self.name, "message": f"Foursquare returned {len(rows)} sample places."}


class GeoapifyAdapter:
    name = "geoapify"
    SEARCH_URL = "https://api.geoapify.com/v1/geocode/search"

    def search(self, *, query: dict[str, Any], api_key: str = "", limit: int = 20) -> list[dict[str, Any]]:
        text = str(query.get("text") or "").strip()
        if not text or not api_key:
            return []
        payload = _get(self.SEARCH_URL, params={"text": text, "limit": min(limit, 20), "format": "json", "apiKey": api_key})
        results = payload.get("results") if isinstance(payload, dict) else payload
        records = []
        for item in (results or [])[:limit]:
            props = item.get("properties") if "properties" in item else item
            name = props.get("name") or props.get("address_line1") or props.get("formatted") or "Unknown"
            records.append(
                _record(
                    source=self.name,
                    source_id=props.get("place_id") or name,
                    name=name,
                    location=props.get("formatted") or props.get("address_line2") or "",
                    website="",
                    industry=props.get("category") or props.get("result_type") or "",
                )
            )
        return records

    def probe(self, api_key: str = "") -> dict[str, Any]:
        rows = self.search(query={"text": "pharmacy in Karachi"}, api_key=api_key, limit=3)
        return {"ok": True, "sample_count": len(rows), "provider": self.name, "message": f"Geoapify returned {len(rows)} sample places."}


class OpenStreetMapAdapter:
    name = "openstreetmap"
    SEARCH_URL = "https://nominatim.openstreetmap.org/search"
    ALLOWED = {"amenity", "shop", "office", "craft", "industrial", "healthcare", "tourism"}

    def search(self, *, query: dict[str, Any], api_key: str = "", limit: int = 20) -> list[dict[str, Any]]:
        text = str(query.get("text") or "").strip()
        if not text:
            return []
        headers = {"User-Agent": USER_AGENT}
        if api_key:
            headers["User-Agent"] = f"{USER_AGENT} {api_key}"
        payload = _get(
            self.SEARCH_URL,
            params={"q": text, "format": "jsonv2", "addressdetails": 1, "limit": min(limit, 20)},
            headers=headers,
        )
        records = []
        items = payload if isinstance(payload, list) else payload.get("results") or []
        for item in items[:limit]:
            cls = str(item.get("class") or item.get("category") or "")
            if cls and cls not in self.ALLOWED and str(item.get("type") or "") not in {"company", "yes"}:
                continue
            records.append(
                _record(
                    source=self.name,
                    source_id=str(item.get("osm_id") or item.get("place_id") or item.get("display_name")),
                    name=item.get("name") or (item.get("display_name") or "Unknown").split(",")[0],
                    location=item.get("display_name") or "",
                    website="",
                    industry=item.get("type") or cls,
                )
            )
        return records

    def probe(self, api_key: str = "") -> dict[str, Any]:
        rows = self.search(query={"text": "cafe in Karachi"}, api_key=api_key, limit=3)
        return {"ok": True, "sample_count": len(rows), "provider": self.name, "message": f"OpenStreetMap Nominatim returned {len(rows)} sample places."}


class OpenCorporatesAdapter:
    name = "opencorporates"
    SEARCH_URL = "https://api.opencorporates.com/v0.4/companies/search"

    def search(self, *, query: dict[str, Any], api_key: str = "", limit: int = 20) -> list[dict[str, Any]]:
        text = str(query.get("text") or "").strip()
        if not text:
            return []
        params: dict[str, Any] = {"q": text, "per_page": min(limit, 20)}
        if api_key:
            params["api_token"] = api_key
        payload = _get(self.SEARCH_URL, params=params)
        companies = ((payload.get("results") or {}).get("companies") or []) if isinstance(payload, dict) else []
        records = []
        for wrapper in companies[:limit]:
            company = wrapper.get("company") or wrapper
            ident = f"{company.get('jurisdiction_code')}-{company.get('company_number')}"
            records.append(
                _record(
                    source=self.name,
                    source_id=ident or company.get("name"),
                    name=company.get("name") or "Unknown",
                    location=company.get("registered_address_in_full") or company.get("jurisdiction_code") or "",
                    website="",
                    industry=company.get("company_type") or "",
                )
            )
        return records

    def probe(self, api_key: str = "") -> dict[str, Any]:
        rows = self.search(query={"text": "textile"}, api_key=api_key, limit=3)
        return {"ok": True, "sample_count": len(rows), "provider": self.name, "message": f"OpenCorporates returned {len(rows)} sample companies."}


class NpiRegistryAdapter:
    name = "npi_registry"
    SEARCH_URL = "https://npiregistry.cms.hhs.gov/api/"

    def search(self, *, query: dict[str, Any], api_key: str = "", limit: int = 20) -> list[dict[str, Any]]:
        text = str(query.get("text") or "").strip()
        if not text:
            return []
        term, city = _split_location(text)
        params: dict[str, Any] = {"version": "2.1", "limit": min(limit, 20), "organization_name": term or text}
        if city:
            params["city"] = city
        payload = _get(self.SEARCH_URL, params=params)
        records = []
        for item in (payload.get("results") or [])[:limit]:
            basic = item.get("basic") or {}
            addresses = item.get("addresses") or []
            loc = addresses[0] if addresses else {}
            taxonomies = item.get("taxonomies") or []
            industry = str((taxonomies[0] or {}).get("desc") or "") if taxonomies else "healthcare"
            name = basic.get("organization_name") or f"{basic.get('first_name', '')} {basic.get('last_name', '')}".strip()
            records.append(
                _record(
                    source=self.name,
                    source_id=str(item.get("number") or name),
                    name=name or "Unknown",
                    location=", ".join(part for part in [loc.get("city"), loc.get("state"), loc.get("country_name")] if part),
                    website="",
                    industry=industry,
                    phone=loc.get("telephone_number") or "",
                )
            )
        return records

    def probe(self, api_key: str = "") -> dict[str, Any]:
        rows = self.search(query={"text": "clinic in Houston"}, api_key=api_key, limit=3)
        return {"ok": True, "sample_count": len(rows), "provider": self.name, "message": f"NPI Registry returned {len(rows)} sample organizations."}


class LinkedInSalesAdapter:
    name = "linkedin_sales_navigator"
    USERINFO = "https://api.linkedin.com/v2/userinfo"

    def __init__(self, search_url: str = ""):
        self.search_url = (search_url or "https://api.linkedin.com/rest/salesApiSearch").strip()

    def search(self, *, query: dict[str, Any], api_key: str = "", limit: int = 20) -> list[dict[str, Any]]:
        text = str(query.get("text") or "").strip()
        if not text or not api_key:
            return []
        payload = _get(
            self.search_url,
            params={"q": "search", "keywords": text, "count": min(limit, 20)},
            headers={
                "Authorization": f"Bearer {api_key}",
                "LinkedIn-Version": "202405",
                "X-Restli-Protocol-Version": "2.0.0",
            },
        )
        elements = payload.get("elements") or payload.get("results") or payload.get("items") or []
        records = []
        for item in elements[:limit]:
            name = item.get("name") or (item.get("company") or {}).get("name") or item.get("localizedName") or "Unknown"
            ident = item.get("id") or item.get("entityUrn") or name
            records.append(
                _record(
                    source=self.name,
                    source_id=str(ident),
                    name=name,
                    location=item.get("location") or item.get("geoLocation") or "",
                    website=item.get("website") or "",
                    industry=item.get("industry") or "",
                )
            )
        return records

    def probe(self, api_key: str = "") -> dict[str, Any]:
        if not api_key:
            raise ProviderUnavailable("Store a LinkedIn Sales Navigator access token before testing.")
        _get(self.USERINFO, headers={"Authorization": f"Bearer {api_key}"})
        return {
            "ok": True,
            "sample_count": 1,
            "provider": self.name,
            "message": "LinkedIn accepted the token. Search uses your SNAP search URL when discovery runs.",
        }


class HttpJsonLeadAdapter:
    name = "http_json"

    def __init__(self, source):
        self.source = source
        self.name = source.code
        self.config = source.public_config or {}

    def search(self, *, query: dict[str, Any], api_key: str = "", limit: int = 20) -> list[dict[str, Any]]:
        text = str(query.get("text") or "").strip()
        url = str(self.config.get("search_url") or "").strip()
        if not text:
            return []
        if not url:
            raise ProviderUnavailable(
                f"{self.source.display_name} has no licensed search URL. Add one in the platform console. SIPulse does not scrape directory websites."
            )
        if self.source.requires_key and not api_key:
            return []
        headers: dict[str, str] = {}
        params: dict[str, Any] = {"q": text, "query": text, "limit": min(limit, 20)}
        auth = str(self.config.get("auth_style") or "bearer")
        if api_key and auth == "bearer":
            headers["Authorization"] = f"Bearer {api_key}"
        elif api_key and auth == "header":
            headers["X-API-Key"] = api_key
        elif api_key:
            params["key"] = api_key
            params["api_key"] = api_key
        payload = _get(url, params=params, headers=headers)
        rows = payload
        path = str(self.config.get("results_path") or "results")
        if isinstance(payload, dict):
            rows = payload
            for part in path.split("."):
                if isinstance(rows, dict):
                    rows = rows.get(part) or []
        records = []
        name_field = self.config.get("name_field") or "name"
        id_field = self.config.get("id_field") or "id"
        address_field = self.config.get("address_field") or "address"
        website_field = self.config.get("website_field") or "website"
        industry_field = self.config.get("industry_field") or "category"
        phone_field = self.config.get("phone_field") or "phone"
        email_field = self.config.get("email_field") or "email"
        for item in (rows or [])[:limit]:
            if not isinstance(item, dict):
                continue
            name = str(item.get(name_field) or item.get("company_name") or "Unknown")
            records.append(
                _record(
                    source=self.name,
                    source_id=str(item.get(id_field) or name),
                    name=name,
                    location=str(item.get(address_field) or item.get("location") or ""),
                    website=str(item.get(website_field) or ""),
                    industry=str(item.get(industry_field) or item.get("industry") or ""),
                    phone=str(item.get(phone_field) or ""),
                    email=str(item.get(email_field) or ""),
                )
            )
        return records

    def probe(self, api_key: str = "") -> dict[str, Any]:
        rows = self.search(query={"text": "dentist in Karachi"}, api_key=api_key, limit=3)
        return {
            "ok": True,
            "sample_count": len(rows),
            "provider": self.name,
            "message": f"{self.source.display_name} returned {len(rows)} sample records.",
        }
