from __future__ import annotations

import secrets as std_secrets

from django.utils import timezone

from apps.billing.entitlements import tenant_module_codes
from apps.common.exceptions import APIError
from apps.crawler.ssrf import SSRFBlocked, validate_public_http_url
from apps.integrations.catalog import PROVIDER_BY_CODE, PROVIDERS, SECRET_KEYS, URL_KEYS, WEBHOOK_EVENTS
from apps.integrations.google import extract_spreadsheet_id, parse_service_account_json, probe_google_sheets
from apps.integrations.models import CRMConnection
from apps.integrations.probes import probe_custom_api, probe_hubspot, probe_odoo, probe_webhook


def _public_config(config: dict) -> dict:
    return {key: value for key, value in (config or {}).items() if key not in SECRET_KEYS}


def serialize_connection(spec: dict, connection: CRMConnection | None, *, modules: set[str]) -> dict:
    required = spec.get("required_module")
    locked = bool(required and required not in modules)
    payload = {
        "code": spec["code"],
        "name": spec["name"],
        "category": spec["category"],
        "description": spec["description"],
        "connectable": spec["connectable"],
        "fields": spec["fields"],
        "setup_steps": spec.get("setup_steps") or [],
        "required_module": required,
        "locked": locked,
        "lock_reason": "Available on Scale and Enterprise." if locked else "",
        "status": "available" if spec["code"] == "native" and not locked else "disconnected",
        "credentials_configured": False,
        "enabled": True,
        "config": {},
        "last_checked_at": None,
        "last_error": "",
        "last_sync_at": None,
        "records_synced": 0,
    }
    if spec["code"] == "native" and not locked:
        payload["status"] = "available"
    if connection is not None:
        payload.update(
            {
                "status": connection.status,
                "credentials_configured": connection.credentials_configured,
                "enabled": connection.enabled,
                "config": _public_config(connection.config),
                "last_checked_at": connection.last_checked_at.isoformat() if connection.last_checked_at else None,
                "last_error": connection.last_error,
                "last_sync_at": connection.last_sync_at.isoformat() if connection.last_sync_at else None,
                "records_synced": connection.records_synced,
            }
        )
    return payload


def list_integrations(tenant) -> list[dict]:
    modules = tenant_module_codes(tenant)
    connections = {item.provider: item for item in CRMConnection.objects.for_tenant(tenant)}
    return [serialize_connection(spec, connections.get(spec["code"]), modules=modules) for spec in PROVIDERS]


def list_commerce_stores(tenant) -> list[dict]:
    return [item for item in list_integrations(tenant) if item.get("category") == "commerce"]


def _require_provider(code: str) -> dict:
    spec = PROVIDER_BY_CODE.get(code)
    if spec is None:
        raise APIError("Unknown integration.", code="NOT_FOUND", status_code=404)
    return spec


def _require_unlocked(tenant, spec: dict) -> None:
    if not spec["connectable"]:
        raise APIError("This integration does not accept API credentials.", code="VALIDATION_ERROR")
    required = spec.get("required_module")
    if required and required not in tenant_module_codes(tenant):
        raise APIError("This integration is not included in the current package.", code="FEATURE_DISABLED", status_code=403)


def _validate_url_fields(public: dict) -> None:
    for key in URL_KEYS:
        value = public.get(key)
        if not value:
            continue
        try:
            public[key] = validate_public_http_url(str(value))
        except SSRFBlocked as exc:
            raise APIError(str(exc.detail), code="VALIDATION_ERROR") from exc


def _as_bool(value, default: bool = True) -> bool:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"1", "true", "yes", "on"}


def _secret_present(field: dict, encrypted: dict) -> bool:
    key = field["key"]
    if encrypted.get(key):
        return True
    return key == "service_account_json" and bool(encrypted.get("private_key"))


def _normalize_events(value) -> list[str]:
    if value in (None, ""):
        return list(WEBHOOK_EVENTS)
    if isinstance(value, str):
        items = [item.strip() for item in value.split(",") if item.strip()]
    elif isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
    else:
        raise APIError("Events must be a list.", code="VALIDATION_ERROR")
    unknown = [item for item in items if item not in WEBHOOK_EVENTS]
    if unknown:
        raise APIError("One or more webhook events are invalid.", code="VALIDATION_ERROR")
    return items


def save_integration(tenant, provider: str, payload: dict) -> tuple[CRMConnection, dict]:
    spec = _require_provider(provider)
    _require_unlocked(tenant, spec)
    revealed: dict[str, str] = {}
    public: dict = {}
    secret_values: dict = {}
    for field in spec["fields"]:
        key = field["key"]
        value = payload.get(key)
        if field.get("input") == "toggle":
            if key in payload:
                public[key] = _as_bool(value)
            continue
        if key == "events":
            public["events"] = _normalize_events(value)
            continue
        if value in (None, ""):
            continue
        if field.get("secret"):
            secret_values[key] = str(value).strip()
        else:
            public[key] = str(value).strip()
    if provider == "google_sheets" and secret_values.get("service_account_json"):
        email, key = parse_service_account_json(secret_values.pop("service_account_json"))
        secret_values["private_key"] = key
        public["client_email"] = email
    _validate_url_fields(public)
    connection = CRMConnection.objects.filter(tenant=tenant, provider=provider).first()
    encrypted = dict(connection.encrypted_config or {}) if connection else {}
    encrypted.update(secret_values)
    current_public = dict(connection.config or {}) if connection else {}
    current_public.update(public)
    if provider == "google_sheets" and current_public.get("spreadsheet_id"):
        current_public["spreadsheet_id"] = extract_spreadsheet_id(str(current_public["spreadsheet_id"]))
    for field in spec["fields"]:
        if field.get("input") == "toggle" and field["key"] not in current_public:
            current_public[field["key"]] = True
        if field.get("required") and field.get("secret") and not _secret_present(field, encrypted):
            raise APIError(f"{field['label']} is required.", code="VALIDATION_ERROR")
        if field.get("required") and not field.get("secret") and not current_public.get(field["key"]):
            raise APIError(f"{field['label']} is required.", code="VALIDATION_ERROR")
    if provider == "webhook" and not encrypted.get("signing_secret"):
        revealed["signing_secret"] = std_secrets.token_urlsafe(32)
        encrypted["signing_secret"] = revealed["signing_secret"]
    if connection is None:
        connection = CRMConnection(tenant=tenant, provider=provider)
    connection.config = current_public
    connection.encrypted_config = encrypted
    connection.enabled = True
    connection.status = CRMConnection.Status.CONFIGURED
    connection.last_error = ""
    connection.save()
    return connection, revealed


def disconnect_integration(tenant, provider: str) -> CRMConnection:
    spec = _require_provider(provider)
    _require_unlocked(tenant, spec)
    connection = CRMConnection.objects.filter(tenant=tenant, provider=provider).first()
    if connection is None:
        connection = CRMConnection(tenant=tenant, provider=provider)
    connection.status = CRMConnection.Status.DISCONNECTED
    connection.encrypted_config = {}
    connection.config = {}
    connection.enabled = False
    connection.last_error = ""
    connection.last_checked_at = timezone.now()
    connection.save()
    return connection


def test_integration(tenant, provider: str) -> CRMConnection:
    spec = _require_provider(provider)
    _require_unlocked(tenant, spec)
    connection = CRMConnection.objects.filter(tenant=tenant, provider=provider).first()
    if connection is None or not connection.credentials_configured:
        raise APIError("Save credentials before testing the connection.", code="VALIDATION_ERROR")
    public = connection.config or {}
    secret = connection.encrypted_config or {}
    try:
        if provider == "hubspot":
            probe_hubspot(access_token=secret.get("access_token", ""))
        elif provider == "odoo":
            probe_odoo(
                base_url=public.get("base_url", ""),
                database=public.get("database", ""),
                username=public.get("username", ""),
                api_key=secret.get("api_key", ""),
            )
        elif provider == "custom_api":
            probe_custom_api(
                base_url=public.get("base_url", ""),
                api_key=secret.get("api_key", ""),
                health_path=public.get("health_path", ""),
                auth_header=public.get("auth_header", ""),
            )
        elif provider == "webhook":
            probe_webhook(url=public.get("url", ""), signing_secret=secret.get("signing_secret", ""))
        elif provider == "google_sheets":
            probe_google_sheets(
                spreadsheet_id=public.get("spreadsheet_id", ""),
                client_email=public.get("client_email", ""),
                private_key=secret.get("private_key", ""),
            )
        elif provider in {"shopify", "woocommerce", "etsy", "ebay"}:
            from apps.business.stores import probe_store

            probe_store(provider, public=public, secret=secret)
        else:
            raise APIError("This integration cannot be tested.", code="VALIDATION_ERROR")
    except APIError as exc:
        connection.status = CRMConnection.Status.ERROR
        connection.last_error = str(exc.detail)
        connection.last_checked_at = timezone.now()
        connection.save(update_fields=["status", "last_error", "last_checked_at", "updated_at"])
        raise
    except Exception as exc:
        connection.status = CRMConnection.Status.ERROR
        connection.last_error = str(exc)
        connection.last_checked_at = timezone.now()
        connection.save(update_fields=["status", "last_error", "last_checked_at", "updated_at"])
        raise APIError("The provider could not be reached.", code="INTEGRATION_ERROR") from exc
    connection.status = CRMConnection.Status.CONNECTED
    connection.last_error = ""
    connection.last_checked_at = timezone.now()
    connection.save(update_fields=["status", "last_error", "last_checked_at", "updated_at"])
    return connection


def rotate_webhook_secret(tenant) -> tuple[CRMConnection, str]:
    connection = CRMConnection.objects.filter(tenant=tenant, provider="webhook").first()
    if connection is None or not (connection.config or {}).get("url"):
        raise APIError("Save a webhook URL before rotating the signing secret.", code="VALIDATION_ERROR")
    _require_unlocked(tenant, _require_provider("webhook"))
    secret = std_secrets.token_urlsafe(32)
    encrypted = dict(connection.encrypted_config or {})
    encrypted["signing_secret"] = secret
    connection.encrypted_config = encrypted
    connection.status = CRMConnection.Status.CONFIGURED
    connection.save(update_fields=["encrypted_config", "status", "updated_at"])
    return connection, secret
