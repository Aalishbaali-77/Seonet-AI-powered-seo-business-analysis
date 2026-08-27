from __future__ import annotations

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from apps.common.exceptions import APIError
from apps.crawler.ssrf import SSRFBlocked, validate_public_http_url

WORKSPACE_DEFAULTS = {
    "timezone": "UTC",
    "locale": "en-US",
    "currency": "USD",
    "company_legal_name": "",
    "company_website": "",
    "industry": "",
    "support_email": "",
    "reply_to_email": "",
    "notification_digest": "daily",
    "primary_crm": "native",
}

ALLOWED_CURRENCIES = {"USD", "EUR", "GBP", "AED", "SAR", "PKR", "INR", "CAD", "AUD"}
ALLOWED_DIGESTS = {"off", "daily", "weekly"}
ALLOWED_PRIMARY_CRM = {"native", "hubspot", "odoo", "custom_api"}


def workspace_profile(tenant) -> dict:
    stored = tenant.settings if isinstance(getattr(tenant, "settings", None), dict) else {}
    profile = dict(WORKSPACE_DEFAULTS)
    for key in WORKSPACE_DEFAULTS:
        value = stored.get(key, profile[key])
        profile[key] = value if value is not None else profile[key]
    return profile


def validate_timezone(value: str) -> str:
    token = (value or "UTC").strip() or "UTC"
    try:
        ZoneInfo(token)
    except ZoneInfoNotFoundError as exc:
        raise APIError("That timezone is not valid.", code="VALIDATION_ERROR") from exc
    return token


def merge_workspace_settings(tenant, payload: dict) -> dict:
    current = workspace_profile(tenant)
    next_settings = dict(tenant.settings or {})
    if "timezone" in payload and payload["timezone"] is not None:
        current["timezone"] = validate_timezone(payload["timezone"])
    if "locale" in payload and payload["locale"] is not None:
        locale = str(payload["locale"]).strip() or "en-US"
        if len(locale) > 16:
            raise APIError("Locale is too long.", code="VALIDATION_ERROR")
        current["locale"] = locale
    if "currency" in payload and payload["currency"] is not None:
        currency = str(payload["currency"]).strip().upper()
        if currency not in ALLOWED_CURRENCIES:
            raise APIError("That currency is not supported.", code="VALIDATION_ERROR")
        current["currency"] = currency
    if "company_legal_name" in payload and payload["company_legal_name"] is not None:
        current["company_legal_name"] = str(payload["company_legal_name"]).strip()[:255]
    if "industry" in payload and payload["industry"] is not None:
        current["industry"] = str(payload["industry"]).strip()[:120]
    if "support_email" in payload and payload["support_email"] is not None:
        current["support_email"] = str(payload["support_email"]).strip().lower()[:254]
    if "reply_to_email" in payload and payload["reply_to_email"] is not None:
        current["reply_to_email"] = str(payload["reply_to_email"]).strip().lower()[:254]
    if "notification_digest" in payload and payload["notification_digest"] is not None:
        digest = str(payload["notification_digest"]).strip()
        if digest not in ALLOWED_DIGESTS:
            raise APIError("Notification digest must be off, daily, or weekly.", code="VALIDATION_ERROR")
        current["notification_digest"] = digest
    if "primary_crm" in payload and payload["primary_crm"] is not None:
        primary = str(payload["primary_crm"]).strip()
        if primary not in ALLOWED_PRIMARY_CRM:
            raise APIError("Primary CRM is invalid.", code="VALIDATION_ERROR")
        current["primary_crm"] = primary
    if "company_website" in payload and payload["company_website"] is not None:
        website = str(payload["company_website"]).strip()
        if website:
            try:
                website = validate_public_http_url(website)
            except SSRFBlocked as exc:
                raise APIError(str(exc.detail), code="VALIDATION_ERROR") from exc
        current["company_website"] = website
    next_settings.update(current)
    return next_settings
