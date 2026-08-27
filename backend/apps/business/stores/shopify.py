from __future__ import annotations

from apps.business.stores.http import PAGE_LIMIT, request_json, shopify_host


def probe(*, shop_domain: str, access_token: str) -> None:
    host = shopify_host(shop_domain)
    request_json(
        "GET",
        f"https://{host}/admin/api/2024-10/shop.json",
        headers={"X-Shopify-Access-Token": access_token},
    )


def fetch(*, shop_domain: str, access_token: str) -> dict:
    host = shopify_host(shop_domain)
    headers = {"X-Shopify-Access-Token": access_token}
    products = request_json("GET", f"https://{host}/admin/api/2024-10/products.json", headers=headers, params={"limit": PAGE_LIMIT})
    orders = request_json("GET", f"https://{host}/admin/api/2024-10/orders.json", headers=headers, params={"limit": PAGE_LIMIT, "status": "any"})
    return {"products": _products(products.get("products") or []), "orders": _orders(orders.get("orders") or []), "reviews": []}


def _products(rows: list) -> list[dict]:
    items = []
    for row in rows:
        variant = ((row.get("variants") or [{}])[0]) or {}
        items.append(
            {
                "external_id": str(row.get("id") or ""),
                "name": str(row.get("title") or "")[:255],
                "sku": str(variant.get("sku") or "")[:80],
                "category": str((row.get("product_type") or ""))[:160],
                "unit_price": variant.get("price"),
            }
        )
    return items


def _orders(rows: list) -> list[dict]:
    items = []
    for row in rows:
        customer = row.get("customer") or {}
        address = row.get("billing_address") or row.get("shipping_address") or {}
        name = " ".join(part for part in [customer.get("first_name"), customer.get("last_name")] if part).strip() or str(customer.get("email") or "Shopify customer")
        status = "cancelled" if row.get("cancelled_at") else "placed"
        if str(row.get("financial_status") or "") in {"refunded", "voided"}:
            status = "refunded"
        lines = []
        for line in row.get("line_items") or []:
            lines.append(
                {
                    "sku": str(line.get("sku") or "")[:80],
                    "name": str(line.get("title") or "")[:255],
                    "quantity": line.get("quantity") or 1,
                    "unit_price": line.get("price"),
                    "discount": line.get("total_discount"),
                }
            )
        items.append(
            {
                "external_id": str(row.get("id") or ""),
                "ordered_at": row.get("created_at"),
                "city": str(address.get("city") or "")[:160],
                "currency": str(row.get("currency") or "USD")[:8],
                "status": status,
                "customer": {"name": name[:255], "email": str(customer.get("email") or ""), "city": str(address.get("city") or "")[:160], "external_id": str(customer.get("id") or "")},
                "lines": lines,
            }
        )
    return items
