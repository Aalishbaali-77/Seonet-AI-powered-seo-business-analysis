from __future__ import annotations

from decimal import Decimal

from django.db.models import Count, Sum

from apps.business.models import CatalogProduct, CommerceCustomer, CommerceOrder, CommerceOrderItem, CommerceReview


def commerce_kpis(tenant) -> dict:
    orders = CommerceOrder.objects.for_tenant(tenant)
    products = CatalogProduct.objects.for_tenant(tenant)
    customers = CommerceCustomer.objects.for_tenant(tenant)
    if not orders.exists() and not products.exists() and not customers.exists():
        return {
            "available": False,
            "reason": "No products, customers, or orders have been imported or synced for this workspace.",
            "products": 0,
            "customers": 0,
            "orders": 0,
            "reviews": reviews_payload(tenant),
            "potential_areas": [],
            "by_city": [],
            "by_channel": [],
            "by_source": [],
        }
    placed = orders.filter(status=CommerceOrder.Status.PLACED)
    items = CommerceOrderItem.objects.for_tenant(tenant).filter(order__in=placed)
    revenue = items.aggregate(total=Sum("unit_price"))["total"]
    qty = items.aggregate(total=Sum("quantity"))["total"]
    order_count = placed.count()
    line_revenue = Decimal("0")
    for item in items.only("unit_price", "quantity", "discount"):
        line_revenue += (item.unit_price or 0) * (item.quantity or 0) - (item.discount or 0)
    aov = (line_revenue / order_count) if order_count else None
    by_city = list(
        placed.exclude(city="").values("city").annotate(orders=Count("id")).order_by("-orders")[:12]
    )
    by_channel = list(
        placed.exclude(channel="").values("channel").annotate(orders=Count("id")).order_by("-orders")[:12]
    )
    return {
        "available": order_count > 0,
        "reason": "" if order_count else "Products or customers exist, but no orders have been imported so revenue KPIs are not shown.",
        "products": products.count(),
        "customers": customers.count(),
        "orders": order_count,
        "revenue": str(line_revenue) if order_count else None,
        "average_order_value": str(aov.quantize(Decimal("0.01"))) if aov is not None else None,
        "units": str(qty or 0),
        "by_city": [{"city": row["city"], "orders": row["orders"]} for row in by_city],
        "by_channel": [{"channel": row["channel"], "orders": row["orders"]} for row in by_channel],
        "customer_cities": list(
            customers.exclude(city="").values_list("city", flat=True).distinct().order_by("city")[:50]
        ),
        "by_source": [
            {"source": row["source"], "orders": row["orders"]}
            for row in placed.exclude(source="").values("source").annotate(orders=Count("id")).order_by("-orders")[:12]
        ],
        "reviews": reviews_payload(tenant),
        "potential_areas": [
            {
                "city": row["city"],
                "orders": row["orders"],
                "why": f"FACT: {row['orders']} stored orders list city as {row['city']}.",
            }
            for row in by_city
        ],
        "origin": "fact",
    }


def reviews_payload(tenant) -> dict:
    reviews = CommerceReview.objects.for_tenant(tenant)
    count = reviews.count()
    if not count:
        return {
            "count": 0,
            "average_rating": None,
            "positive": 0,
            "neutral": 0,
            "negative": 0,
            "reason": "No product reviews have been fetched. Shopify and eBay do not expose reviews in this sync.",
            "origin": "fact",
        }
    ratings = [item.rating for item in reviews.exclude(rating__isnull=True)]
    average = (sum(ratings) / len(ratings)) if ratings else None
    return {
        "count": count,
        "average_rating": round(average, 2) if average is not None else None,
        "positive": reviews.filter(sentiment=CommerceReview.Sentiment.POSITIVE).count(),
        "neutral": reviews.filter(sentiment=CommerceReview.Sentiment.NEUTRAL).count(),
        "negative": reviews.filter(sentiment=CommerceReview.Sentiment.NEGATIVE).count(),
        "reason": "",
        "origin": "fact",
    }
