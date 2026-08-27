from __future__ import annotations

from decimal import Decimal
from typing import Any

import httpx

from apps.common.exceptions import APIError

USER_AGENT = "SeonetCommerce/1.0"
TIMEOUT = 20
PAGE_LIMIT = 50


def request_json(
    method: str,
    url: str,
    *,
    headers: dict | None = None,
    params: dict | None = None,
    auth: tuple[str, str] | None = None,
) -> Any:
    with httpx.Client(timeout=TIMEOUT, follow_redirects=False, headers={"User-Agent": USER_AGENT, **(headers or {})}) as client:
        response = client.request(method, url, params=params, auth=auth)
    if response.status_code in {401, 403}:
        raise APIError("The store rejected the credentials.", code="INTEGRATION_AUTH")
    if response.status_code >= 400:
        raise APIError(f"The store returned HTTP {response.status_code}.", code="INTEGRATION_ERROR")
    if not response.content:
        return {}
    try:
        return response.json()
    except ValueError as exc:
        raise APIError("The store did not return JSON.", code="INTEGRATION_ERROR") from exc


def money(value) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value).replace(",", ""))
    except Exception:  # noqa: BLE001
        return None


def shopify_host(domain: str) -> str:
    host = (domain or "").strip().lower().replace("https://", "").replace("http://", "").split("/")[0]
    if not host.endswith(".myshopify.com"):
        host = f"{host}.myshopify.com" if "." not in host else host
    if not host.endswith(".myshopify.com"):
        raise APIError("Shopify shop domain must be your-store.myshopify.com.", code="VALIDATION_ERROR")
    return host
