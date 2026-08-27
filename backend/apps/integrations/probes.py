from __future__ import annotations

import hashlib
import hmac
import json
from urllib.parse import urljoin

import httpx

from apps.common.exceptions import APIError
from apps.crawler.ssrf import validate_public_http_url


USER_AGENT = "SIPulseIntegrations/1.0"
TIMEOUT = 12


def _client() -> httpx.Client:
    return httpx.Client(follow_redirects=False, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT})


def probe_hubspot(*, access_token: str) -> None:
    if not access_token:
        raise APIError("A HubSpot private app token is required.", code="VALIDATION_ERROR")
    with _client() as client:
        response = client.get(
            "https://api.hubapi.com/crm/v3/objects/contacts",
            params={"limit": 1},
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if response.status_code in {401, 403}:
        raise APIError("HubSpot rejected the token.", code="INTEGRATION_AUTH")
    if response.status_code >= 400:
        raise APIError(f"HubSpot returned HTTP {response.status_code}.", code="INTEGRATION_ERROR")


def probe_odoo(*, base_url: str, database: str, username: str, api_key: str) -> None:
    url = validate_public_http_url(base_url.rstrip("/") + "/")
    endpoint = urljoin(url if url.endswith("/") else url + "/", "jsonrpc")
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {"service": "common", "method": "authenticate", "args": [database, username, api_key, {}]},
        "id": 1,
    }
    with _client() as client:
        response = client.post(endpoint, json=payload, headers={"Content-Type": "application/json"})
    if response.status_code >= 400:
        raise APIError(f"Odoo returned HTTP {response.status_code}.", code="INTEGRATION_ERROR")
    try:
        body = response.json()
    except json.JSONDecodeError as exc:
        raise APIError("Odoo did not return JSON-RPC.", code="INTEGRATION_ERROR") from exc
    result = body.get("result")
    if body.get("error") or not result:
        raise APIError("Odoo authentication failed. Check the database, user, and API key.", code="INTEGRATION_AUTH")


def probe_custom_api(*, base_url: str, api_key: str, health_path: str = "", auth_header: str = "") -> None:
    root = validate_public_http_url(base_url)
    path = (health_path or "").strip()
    target = root
    if path:
        if not path.startswith("/"):
            path = f"/{path}"
        target = validate_public_http_url(urljoin(root if root.endswith("/") else root + "/", path.lstrip("/")))
    header_name = (auth_header or "Authorization").strip() or "Authorization"
    headers = {header_name: api_key if header_name.lower() != "authorization" else f"Bearer {api_key}"}
    with _client() as client:
        response = client.get(target, headers=headers)
    if response.status_code in {401, 403}:
        raise APIError("The API rejected the key.", code="INTEGRATION_AUTH")
    if response.status_code >= 400:
        raise APIError(f"The API returned HTTP {response.status_code}.", code="INTEGRATION_ERROR")


def probe_webhook(*, url: str, signing_secret: str) -> None:
    target = validate_public_http_url(url)
    body = json.dumps({"event": "ping", "source": "sipulse"}).encode()
    signature = hmac.new(signing_secret.encode(), body, hashlib.sha256).hexdigest()
    with _client() as client:
        response = client.post(
            target,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-SIPulse-Signature": f"sha256={signature}",
            },
        )
    if response.status_code >= 400:
        raise APIError(f"The webhook returned HTTP {response.status_code}.", code="INTEGRATION_ERROR")
