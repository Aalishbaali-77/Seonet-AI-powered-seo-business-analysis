from typing import Any

import httpx

from providers.ai.base import ProviderUnavailable

PLACES_TEXT_SEARCH = "https://maps.googleapis.com/maps/api/place/textsearch/json"
PLACES_DETAILS = "https://maps.googleapis.com/maps/api/place/details/json"


def place_details(place_id: str, api_key: str) -> dict[str, Any]:
    if not place_id or not api_key:
        return {}
    with httpx.Client(timeout=12, follow_redirects=False) as client:
        response = client.get(
            PLACES_DETAILS,
            params={
                "place_id": place_id,
                "fields": "formatted_phone_number,international_phone_number,website,formatted_address,name",
                "key": api_key,
            },
        )
    if response.status_code >= 400:
        return {}
    payload = response.json() if response.content else {}
    return payload.get("result") or {}


class GooglePlacesAdapter:
    name = "google_places"

    def search(self, *, query: dict[str, Any], api_key: str, limit: int = 20) -> list[dict[str, Any]]:
        text = str(query.get("text") or "").strip()
        if not text or not api_key:
            return []
        with httpx.Client(timeout=15, follow_redirects=False) as client:
            response = client.get(PLACES_TEXT_SEARCH, params={"query": text, "key": api_key})
        if response.status_code >= 400:
            raise ProviderUnavailable(f"Google Places returned HTTP {response.status_code}.")
        payload = response.json()
        status = payload.get("status")
        if status in {"ZERO_RESULTS", "OK"}:
            records: list[dict[str, Any]] = []
            for item in payload.get("results", [])[:limit]:
                types = item.get("types") or []
                records.append(
                    {
                        "source": self.name,
                        "source_record_id": item.get("place_id") or item.get("name"),
                        "company_name": item.get("name") or "Unknown",
                        "location": item.get("formatted_address") or "",
                        "website": "",
                        "industry": str(types[0]).replace("_", " ") if types else "",
                        "phone": "",
                        "email": "",
                    }
                )
            return records
        message = payload.get("error_message") or status or "Google Places request failed."
        raise ProviderUnavailable(message)
