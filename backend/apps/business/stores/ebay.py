from __future__ import annotations

from apps.business.stores.http import PAGE_LIMIT, request_json
from apps.common.exceptions import APIError


def probe(*, access_token: str) -> None:
    if not access_token:
        raise APIError("An eBay user access token is required.", code="VALIDATION_ERROR")
    request_json("GET", "https://api.ebay.com/sell/fulfillment/v1/order", headers={"Authorization": f"Bearer {access_token}"}, params={"limit": 1})


def fetch(*, access_token: str) -> dict:
    payload = request_json(
        "GET",
        "https://api.ebay.com/sell/fulfillment/v1/order",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"limit": PAGE_LIMIT},
    )
    return {"products": [], "orders": _orders((payload or {}).get("orders") or []), "reviews": []}


def _orders(rows: list) -> list[dict]:
    items = []
    for row in rows:
        ship = (((row.get("fulfillmentStartInstructions") or [{}])[0] or {}).get("shippingStep") or {}).get("shipTo") or {}
        address = ship.get("contactAddress") or {}
        buyer = (row.get("buyer") or {}).get("username") or "eBay buyer"
        lines = []
        for line in row.get("lineItems") or []:
            cost = (line.get("lineItemCost") or {}).get("value")
            lines.append(
                {
                    "sku": str(line.get("sku") or "")[:80],
                    "name": str(line.get("title") or "")[:255],
                    "quantity": line.get("quantity") or 1,
                    "unit_price": cost,
                    "discount": 0,
                }
            )
        items.append(
            {
                "external_id": str(row.get("orderId") or ""),
                "ordered_at": row.get("creationDate"),
                "city": str(address.get("city") or "")[:160],
                "currency": str(((row.get("pricingSummary") or {}).get("total") or {}).get("currency") or "USD")[:8],
                "status": "cancelled" if str(row.get("orderFulfillmentStatus") or "") == "CANCELLED" else "placed",
                "customer": {"name": str(buyer)[:255], "email": "", "city": str(address.get("city") or "")[:160], "external_id": str(buyer)[:80]},
                "lines": lines,
            }
        )
    return items
