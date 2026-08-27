from __future__ import annotations

from urllib.parse import urljoin

from apps.business.stores.http import PAGE_LIMIT, request_json
from apps.crawler.ssrf import validate_public_http_url


def _root(base_url: str) -> str:
    return validate_public_http_url(base_url.rstrip("/") + "/")


def probe(*, base_url: str, consumer_key: str, consumer_secret: str) -> None:
    root = _root(base_url)
    request_json(
        "GET",
        urljoin(root, "wp-json/wc/v3/products"),
        auth=(consumer_key, consumer_secret),
        params={"per_page": 1},
    )


def fetch(*, base_url: str, consumer_key: str, consumer_secret: str) -> dict:
    root = _root(base_url)
    auth = (consumer_key, consumer_secret)
    products = request_json("GET", urljoin(root, "wp-json/wc/v3/products"), auth=auth, params={"per_page": PAGE_LIMIT})
    orders = request_json("GET", urljoin(root, "wp-json/wc/v3/orders"), auth=auth, params={"per_page": PAGE_LIMIT})
    reviews = request_json("GET", urljoin(root, "wp-json/wc/v3/products/reviews"), auth=auth, params={"per_page": PAGE_LIMIT})
    return {
        "products": _products(products if isinstance(products, list) else []),
        "orders": _orders(orders if isinstance(orders, list) else []),
        "reviews": _reviews(reviews if isinstance(reviews, list) else []),
    }


def _products(rows: list) -> list[dict]:
    items = []
    for row in rows:
        items.append(
            {
                "external_id": str(row.get("id") or ""),
                "name": str(row.get("name") or "")[:255],
                "sku": str(row.get("sku") or "")[:80],
                "category": str(((row.get("categories") or [{}])[0] or {}).get("name") or "")[:160],
                "unit_price": row.get("price") or row.get("regular_price"),
            }
        )
    return items


def _orders(rows: list) -> list[dict]:
    mapping = {"cancelled": "cancelled", "refunded": "refunded", "failed": "cancelled", "trash": "cancelled"}
    items = []
    for row in rows:
        billing = row.get("billing") or {}
        name = " ".join(part for part in [billing.get("first_name"), billing.get("last_name")] if part).strip() or str(billing.get("email") or "WooCommerce customer")
        lines = []
        for line in row.get("line_items") or []:
            lines.append(
                {
                    "sku": str(line.get("sku") or "")[:80],
                    "name": str(line.get("name") or "")[:255],
                    "quantity": line.get("quantity") or 1,
                    "unit_price": line.get("price"),
                    "discount": 0,
                    "product_external_id": str(line.get("product_id") or ""),
                }
            )
        items.append(
            {
                "external_id": str(row.get("id") or ""),
                "ordered_at": row.get("date_created"),
                "city": str(billing.get("city") or "")[:160],
                "currency": str(row.get("currency") or "USD")[:8],
                "status": mapping.get(str(row.get("status") or ""), "placed"),
                "customer": {
                    "name": name[:255],
                    "email": str(billing.get("email") or ""),
                    "city": str(billing.get("city") or "")[:160],
                    "external_id": str(row.get("customer_id") or ""),
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
                "external_id": str(row.get("id") or ""),
                "product_external_id": str(row.get("product_id") or ""),
                "rating": row.get("rating"),
                "title": "",
                "body": str(row.get("review") or "")[:4000],
                "reviewer": str(row.get("reviewer") or "")[:160],
            }
        )
    return items
