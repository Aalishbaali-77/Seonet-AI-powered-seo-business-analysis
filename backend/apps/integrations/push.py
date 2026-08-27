from __future__ import annotations

import hashlib
import hmac
import json
import logging
from urllib.parse import urljoin, urlparse

from django.db.models import F
from django.utils import timezone

from apps.billing.entitlements import tenant_module_codes
from apps.common.exceptions import APIError
from apps.crawler.ssrf import validate_public_http_url
from apps.integrations.catalog import PUSH_PROVIDERS
from apps.integrations.google import LEAD_HEADERS, RESULT_HEADERS, append_sheet_row
from apps.integrations.models import CRMConnection
from apps.integrations.probes import _client

logger = logging.getLogger(__name__)


def _flag(config: dict, key: str, default: bool = True) -> bool:
    value = (config or {}).get(key)
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"1", "true", "yes", "on"}


def _iso(value) -> str:
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _domain(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url if "://" in url else f"https://{url}")
    return (parsed.netloc or parsed.path).replace("www.", "").split(":")[0].lower()


def lead_payload(lead) -> dict:
    return {
        "id": str(lead.id),
        "company_name": lead.company_name,
        "industry": lead.industry,
        "location": lead.location,
        "website": lead.website,
        "phone": lead.phone,
        "email": lead.email,
        "status": lead.status,
        "lead_score": lead.lead_score,
        "opportunity_score": lead.opportunity_score,
        "source": lead.source,
        "notes": lead.notes,
        "ai_summary": lead.ai_summary,
        "created_at": _iso(lead.created_at),
        "updated_at": _iso(lead.updated_at),
    }


def audit_payload(audit) -> dict:
    website = audit.website
    scores = audit.scores or {}
    return {
        "id": str(audit.id),
        "website": getattr(website, "url", ""),
        "domain": getattr(website, "domain", ""),
        "name": getattr(website, "name", "") or getattr(website, "business_name", "") or getattr(website, "domain", ""),
        "overall_score": audit.overall_score,
        "scores": scores,
        "pages_crawled": audit.pages_crawled,
        "issue_count": audit.issue_count,
        "completed_at": _iso(audit.completed_at),
    }


def _wants(connection: CRMConnection, kind: str, event: str) -> bool:
    config = connection.config or {}
    if connection.provider == "webhook":
        events = config.get("events") or []
        return event in events
    key = "push_leads" if kind == "lead" else "push_results"
    return _flag(config, key, True)


def _destinations(tenant, kind: str, event: str):
    if "integrations" not in tenant_module_codes(tenant):
        return []
    connections = CRMConnection.objects.filter(
        tenant=tenant,
        enabled=True,
        provider__in=PUSH_PROVIDERS,
        status__in=[CRMConnection.Status.CONFIGURED, CRMConnection.Status.CONNECTED, CRMConnection.Status.ERROR],
    )
    return [
        item
        for item in connections
        if item.credentials_configured and _wants(item, kind, event)
    ]


def _mark_ok(connection: CRMConnection) -> None:
    CRMConnection.objects.filter(id=connection.id).update(
        records_synced=F("records_synced") + 1,
        last_sync_at=timezone.now(),
        last_error="",
        status=CRMConnection.Status.CONNECTED,
        updated_at=timezone.now(),
    )


def _mark_error(connection: CRMConnection, exc: Exception) -> None:
    message = str(getattr(exc, "detail", "") or exc)[:2000]
    CRMConnection.objects.filter(id=connection.id).update(
        last_error=message,
        last_checked_at=timezone.now(),
        updated_at=timezone.now(),
    )
    logger.warning("integration push failed provider=%s error=%s", connection.provider, message)


def _dispatch(tenant, kind: str, event: str, sender) -> bool:
    any_ok = False
    for connection in _destinations(tenant, kind, event):
        try:
            sender(connection)
            _mark_ok(connection)
            any_ok = True
        except Exception as exc:  # noqa: BLE001
            _mark_error(connection, exc)
    return any_ok


def push_lead(tenant, lead, *, event: str = "lead.created") -> None:
    try:
        payload = lead_payload(lead)
        ok = _dispatch(tenant, "lead", event, lambda conn: send_lead(conn, payload, event=event))
        if ok and not lead.crm_synced:
            lead.crm_synced = True
            lead.save(update_fields=["crm_synced", "updated_at"])
    except Exception:  # noqa: BLE001
        logger.exception("lead push failed lead_id=%s", getattr(lead, "id", None))


def deal_payload(deal) -> dict:
    return {
        "id": str(deal.id),
        "name": deal.name,
        "amount": str(deal.amount),
        "stage": str(deal.stage_id),
        "company": str(deal.company_id),
        "lead": str(deal.lead_id) if deal.lead_id else None,
    }


def push_deal(tenant, deal, *, event: str = "deal.created") -> None:
    try:
        payload = deal_payload(deal)
        for connection in _destinations(tenant, "lead", event):
            if connection.provider not in {"webhook", "custom_api"}:
                continue
            try:
                if connection.provider == "webhook":
                    _webhook_post(connection, event, payload)
                else:
                    _custom_post(connection, payload, path_key="deals_path", default="/deals", event=event)
                _mark_ok(connection)
            except Exception as exc:  # noqa: BLE001
                _mark_error(connection, exc)
    except Exception:  # noqa: BLE001
        logger.exception("deal push failed deal_id=%s", getattr(deal, "id", None))


def push_audit(tenant, audit) -> None:
    try:
        payload = audit_payload(audit)
        _dispatch(tenant, "result", "audit.completed", lambda conn: send_result(conn, payload))
    except Exception:  # noqa: BLE001
        logger.exception("audit push failed audit_id=%s", getattr(audit, "id", None))


def send_lead(connection: CRMConnection, payload: dict, *, event: str) -> None:
    if connection.provider == "hubspot":
        _hubspot_lead(connection, payload)
    elif connection.provider == "odoo":
        _odoo_lead(connection, payload)
    elif connection.provider == "custom_api":
        _custom_post(connection, payload, path_key="leads_path", default="/leads", event=event)
    elif connection.provider == "google_sheets":
        _sheets_lead(connection, payload)
    elif connection.provider == "webhook":
        _webhook_post(connection, event, payload)
    else:
        raise APIError("Unknown destination.", code="VALIDATION_ERROR")


def send_result(connection: CRMConnection, payload: dict) -> None:
    if connection.provider == "hubspot":
        _hubspot_result(connection, payload)
    elif connection.provider == "odoo":
        _odoo_result(connection, payload)
    elif connection.provider == "custom_api":
        _custom_post(connection, payload, path_key="results_path", default="/results", event="audit.completed")
    elif connection.provider == "google_sheets":
        _sheets_result(connection, payload)
    elif connection.provider == "webhook":
        _webhook_post(connection, "audit.completed", payload)
    else:
        raise APIError("Unknown destination.", code="VALIDATION_ERROR")


def _raise_http(provider: str, response) -> None:
    if response.status_code in {401, 403}:
        raise APIError(f"{provider} rejected the credentials.", code="INTEGRATION_AUTH")
    if response.status_code >= 400:
        raise APIError(f"{provider} returned HTTP {response.status_code}.", code="INTEGRATION_ERROR")


def _hubspot_headers(connection: CRMConnection) -> dict:
    token = (connection.encrypted_config or {}).get("access_token") or ""
    if not token:
        raise APIError("A HubSpot private app token is required.", code="VALIDATION_ERROR")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _hubspot_lead(connection: CRMConnection, payload: dict) -> None:
    domain = _domain(payload.get("website") or "")
    properties = {
        "name": payload.get("company_name") or domain or "Seonet lead",
        "phone": payload.get("phone") or "",
        "website": payload.get("website") or "",
        "description": payload.get("notes") or payload.get("ai_summary") or "",
    }
    if domain:
        properties["domain"] = domain
    with _client() as client:
        response = client.post(
            "https://api.hubapi.com/crm/v3/objects/companies",
            json={"properties": properties},
            headers=_hubspot_headers(connection),
        )
        _raise_http("HubSpot", response)
        email = (payload.get("email") or "").strip()
        if not email:
            return
        contact = client.post(
            "https://api.hubapi.com/crm/v3/objects/contacts",
            json={"properties": {"email": email, "company": properties["name"]}},
            headers=_hubspot_headers(connection),
        )
        if contact.status_code not in {401, 403} and contact.status_code >= 400 and contact.status_code != 409:
            _raise_http("HubSpot", contact)


def _hubspot_result(connection: CRMConnection, payload: dict) -> None:
    scores = payload.get("scores") or {}
    body = (
        f"Seonet audit for {payload.get('website') or payload.get('domain')}\n"
        f"Overall: {payload.get('overall_score')}\n"
        f"Technical SEO: {scores.get('technical_seo')}\n"
        f"On-page SEO: {scores.get('on_page_seo')}\n"
        f"AEO: {scores.get('aeo')}\n"
        f"GEO: {scores.get('geo')}\n"
        f"Pages: {payload.get('pages_crawled')} · Issues: {payload.get('issue_count')}"
    )
    domain = payload.get("domain") or _domain(payload.get("website") or "")
    properties = {"name": payload.get("name") or domain or "Seonet audit"}
    if domain:
        properties["domain"] = domain
    if payload.get("website"):
        properties["website"] = payload["website"]
    headers = _hubspot_headers(connection)
    with _client() as client:
        company = client.post(
            "https://api.hubapi.com/crm/v3/objects/companies",
            json={"properties": properties},
            headers=headers,
        )
        _raise_http("HubSpot", company)
        note = client.post(
            "https://api.hubapi.com/crm/v3/objects/notes",
            json={"properties": {"hs_note_body": body, "hs_timestamp": timezone.now().isoformat()}},
            headers=headers,
        )
        if note.status_code >= 400:
            _raise_http("HubSpot", note)


def _odoo_rpc(base_url: str, payload: dict):
    url = validate_public_http_url(base_url.rstrip("/") + "/")
    endpoint = urljoin(url if url.endswith("/") else url + "/", "jsonrpc")
    with _client() as client:
        response = client.post(endpoint, json=payload, headers={"Content-Type": "application/json"})
    if response.status_code >= 400:
        raise APIError(f"Odoo returned HTTP {response.status_code}.", code="INTEGRATION_ERROR")
    try:
        body = response.json()
    except json.JSONDecodeError as exc:
        raise APIError("Odoo did not return JSON-RPC.", code="INTEGRATION_ERROR") from exc
    if body.get("error"):
        raise APIError("Odoo rejected the request. Check the database, user, and API key.", code="INTEGRATION_AUTH")
    return body.get("result")


def _odoo_uid(connection: CRMConnection) -> tuple[str, str, int, str]:
    public = connection.config or {}
    secret = connection.encrypted_config or {}
    database = public.get("database") or ""
    username = public.get("username") or ""
    api_key = secret.get("api_key") or ""
    uid = _odoo_rpc(
        public.get("base_url") or "",
        {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {"service": "common", "method": "authenticate", "args": [database, username, api_key, {}]},
            "id": 1,
        },
    )
    if not uid:
        raise APIError("Odoo authentication failed. Check the database, user, and API key.", code="INTEGRATION_AUTH")
    return public.get("base_url") or "", database, int(uid), api_key


def _odoo_execute(base_url: str, database: str, uid: int, api_key: str, model: str, method: str, args: list):
    return _odoo_rpc(
        base_url,
        {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {"service": "object", "method": "execute_kw", "args": [database, uid, api_key, model, method, args]},
            "id": 2,
        },
    )


def _odoo_lead(connection: CRMConnection, payload: dict) -> None:
    base_url, database, uid, api_key = _odoo_uid(connection)
    values = {
        "name": payload.get("company_name") or "Seonet lead",
        "is_company": True,
        "website": payload.get("website") or "",
        "phone": payload.get("phone") or "",
        "email": payload.get("email") or "",
        "comment": payload.get("notes") or payload.get("ai_summary") or "",
    }
    _odoo_execute(base_url, database, uid, api_key, "res.partner", "create", [values])


def _odoo_result(connection: CRMConnection, payload: dict) -> None:
    base_url, database, uid, api_key = _odoo_uid(connection)
    scores = payload.get("scores") or {}
    comment = (
        f"Seonet audit overall {payload.get('overall_score')}. "
        f"Technical SEO {scores.get('technical_seo')}, AEO {scores.get('aeo')}, GEO {scores.get('geo')}. "
        f"Pages {payload.get('pages_crawled')}, issues {payload.get('issue_count')}."
    )
    values = {
        "name": payload.get("name") or payload.get("domain") or "Seonet audit",
        "is_company": True,
        "website": payload.get("website") or "",
        "comment": comment,
    }
    _odoo_execute(base_url, database, uid, api_key, "res.partner", "create", [values])


def _custom_post(connection: CRMConnection, payload: dict, *, path_key: str, default: str, event: str) -> None:
    public = connection.config or {}
    secret = connection.encrypted_config or {}
    api_key = secret.get("api_key") or ""
    root = validate_public_http_url(public.get("base_url") or "")
    path = (public.get(path_key) or default).strip() or default
    if not path.startswith("/"):
        path = f"/{path}"
    target = validate_public_http_url(urljoin(root if root.endswith("/") else root + "/", path.lstrip("/")))
    header_name = (public.get("auth_header") or "Authorization").strip() or "Authorization"
    headers = {header_name: api_key if header_name.lower() != "authorization" else f"Bearer {api_key}"}
    body = {"event": event, "source": "seonet", "data": payload}
    with _client() as client:
        response = client.post(target, json=body, headers=headers)
    _raise_http("The API", response)


def _webhook_post(connection: CRMConnection, event: str, payload: dict) -> None:
    public = connection.config or {}
    secret = (connection.encrypted_config or {}).get("signing_secret") or ""
    target = validate_public_http_url(public.get("url") or "")
    body = json.dumps({"event": event, "source": "seonet", "data": payload}, default=str).encode()
    signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    with _client() as client:
        response = client.post(
            target,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Seonet-Signature": f"sha256={signature}",
            },
        )
    _raise_http("The webhook", response)


def _sheets_lead(connection: CRMConnection, payload: dict) -> None:
    public = connection.config or {}
    secret = connection.encrypted_config or {}
    append_sheet_row(
        spreadsheet_id=public.get("spreadsheet_id") or "",
        tab=(public.get("leads_tab") or "Leads").strip() or "Leads",
        headers=LEAD_HEADERS,
        row=[
            payload.get("company_name") or "",
            payload.get("industry") or "",
            payload.get("location") or "",
            payload.get("website") or "",
            payload.get("phone") or "",
            payload.get("email") or "",
            payload.get("status") or "",
            payload.get("lead_score") if payload.get("lead_score") is not None else "",
            payload.get("opportunity_score") if payload.get("opportunity_score") is not None else "",
            payload.get("source") or "",
            payload.get("notes") or "",
            payload.get("created_at") or "",
        ],
        client_email=public.get("client_email") or "",
        private_key=secret.get("private_key") or "",
    )


def _sheets_result(connection: CRMConnection, payload: dict) -> None:
    public = connection.config or {}
    secret = connection.encrypted_config or {}
    scores = payload.get("scores") or {}
    append_sheet_row(
        spreadsheet_id=public.get("spreadsheet_id") or "",
        tab=(public.get("results_tab") or "Audit results").strip() or "Audit results",
        headers=RESULT_HEADERS,
        row=[
            payload.get("website") or payload.get("domain") or "",
            payload.get("name") or "",
            payload.get("overall_score") if payload.get("overall_score") is not None else "",
            scores.get("technical_seo", ""),
            scores.get("on_page_seo", ""),
            scores.get("aeo", ""),
            scores.get("geo", ""),
            payload.get("pages_crawled") if payload.get("pages_crawled") is not None else "",
            payload.get("issue_count") if payload.get("issue_count") is not None else "",
            payload.get("completed_at") or "",
        ],
        client_email=public.get("client_email") or "",
        private_key=secret.get("private_key") or "",
    )
