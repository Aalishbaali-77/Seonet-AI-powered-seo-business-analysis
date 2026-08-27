from __future__ import annotations

from apps.business.stores.http import PAGE_LIMIT, request_json
from apps.common.exceptions import APIError


def _headers(*, api_key: str, access_token: str) -> dict:
    if not api_key or not access_token:
        raise APIError("Etsy API key and access token are required.", code="VALIDATION_ERROR")
    return {"x-api-key": api_key, "Authorization": f"Bearer {access_token}"}


def probe(*, shop_id: str, api_key: str, access_token: str) -> None:
    request_json("GET", f"https://openapi.etsy.com/v3/application/shops/{shop_id}", headers=_headers(api_key=api_key, access_token=access_token))


def fetch(*, shop_id: str, api_key: str, access_token: str) -> dict:
    headers = _headers(api_key=api_key, access_token=access_token)
    listings = request_json("GET", f"https://openapi.etsy.com/v3/application/shops/{shop_id}/listings/active", headers=headers, params={"limit": PAGE_LIMIT})
    receipts = request_json("GET", f"https://openapi.etsy.com/v3/application/shops/{shop_id}/receipts", headers=headers, params={"limit": PAGE_LIMIT})
    reviews = request_json("GET", f"https://openapi.etsy.com/v3/application/shops/{shop_id}/reviews", headers=headers, params={"limit": PAGE_LIMIT})
    return {
        "products": _products((listings or {}).get("results") or []),
        "orders": _orders((receipts or {}).get("results") or []),
        "reviews": _reviews((reviews or {}).get("results") or []),
    }


def _amount(payload) -> str | None:
    if not isinstance(payload, dict):
        return None
    amount = payload.get("amount")
    divisor = payload.get("divisor") or 100
    if amount is None:
        return None
    try:
        return str(int(amount) / int(divisor))
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _products(rows: list) -> list[dict]:
    items = []
    for row in rows:
        items.append(
            {
                "external_id": str(row.get("listing_id") or ""),
                "name": str(row.get("title") or "")[:255],
                "sku": str(row.get("sku") or "")[:80],
                "category": "",
                "unit_price": _amount(row.get("price") or {}),
            }
        )
    return items


def _orders(rows: list) -> list[dict]:
    items = []
    for row in rows:
        lines = []
        for line in row.get("transactions") or []:
            lines.append(
                {
                    "sku": str(line.get("sku") or "")[:80],
                    "name": str(line.get("title") or "")[:255],
                    "quantity": line.get("quantity") or 1,
                    "unit_price": _amount(line.get("price") or {}),
                    "discount": 0,
                    "product_external_id": str(line.get("listing_id") or ""),
                }
            )
        created = row.get("created_timestamp")
        ordered_at = None
        if created:
            from datetime import datetime, timezone

            ordered_at = datetime.fromtimestamp(int(created), tz=timezone.utc).isoformat()
        items.append(
            {
                "external_id": str(row.get("receipt_id") or ""),
                "ordered_at": ordered_at,
                "city": str(row.get("city") or "")[:160],
                "currency": str(((row.get("grandtotal") or {}).get("currency_code")) or "USD")[:8],
                "status": "placed",
                "customer": {
                    "name": str(row.get("name") or "Etsy buyer")[:255],
                    "email": str(row.get("buyer_email") or ""),
                    "city": str(row.get("city") or "")[:160],
                    "external_id": str(row.get("buyer_user_id") or ""),
                },
                "lines": lines,
            }
        )
    return items


def _reviews(rows: list) -> list[dict]:
    items = []
    for row in rows:
        items.append(
            {
                "external_id": str(row.get("listing_id") or row.get("transaction_id") or ""),
                "product_external_id": str(row.get("listing_id") or ""),
                "rating": row.get("rating"),
                "title": "",
                "body": str(row.get("review") or "")[:4000],
                "reviewer": "",
            }
        )
    return items
