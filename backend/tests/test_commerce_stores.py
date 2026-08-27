from __future__ import annotations

import pytest

from apps.business.kpis import commerce_kpis
from apps.business.models import CatalogProduct, CommerceCustomer, CommerceOrder, CommerceReview
from apps.business.sync import apply_payload, promote_customers_to_leads, sentiment_from_rating
from apps.integrations.models import CRMConnection
from apps.leads.models import Lead


@pytest.mark.django_db
def test_sentiment_buckets_from_star_ratings():
    assert sentiment_from_rating(5) == CommerceReview.Sentiment.POSITIVE
    assert sentiment_from_rating(3) == CommerceReview.Sentiment.NEUTRAL
    assert sentiment_from_rating(1) == CommerceReview.Sentiment.NEGATIVE
    assert sentiment_from_rating(None) == ""


@pytest.mark.django_db
def test_store_payload_upserts_orders_reviews_and_kpis(tenant, other_tenant):
    payload = {
        "products": [{"external_id": "p1", "name": "Bar", "sku": "BAR", "category": "Food", "unit_price": "10"}],
        "orders": [
            {
                "external_id": "o1",
                "ordered_at": "2026-01-02T10:00:00Z",
                "city": "Lahore",
                "currency": "PKR",
                "status": "placed",
                "customer": {"name": "Ayesha", "email": "ayesha@example.com", "city": "Lahore", "external_id": "c1"},
                "lines": [{"sku": "BAR", "name": "Bar", "quantity": 2, "unit_price": "10", "discount": 0, "product_external_id": "p1"}],
            }
        ],
        "reviews": [{"external_id": "r1", "product_external_id": "p1", "rating": 5, "body": "Great", "reviewer": "Ayesha"}],
    }
    counts = apply_payload(tenant, "woocommerce", payload)
    assert counts == {"products": 1, "orders": 1, "reviews": 1}
    apply_payload(tenant, "woocommerce", payload)
    assert CatalogProduct.objects.for_tenant(tenant).filter(source="woocommerce").count() == 1
    assert CommerceOrder.objects.for_tenant(tenant).filter(external_id="o1").count() == 1
    kpis = commerce_kpis(tenant)
    assert kpis["available"] is True
    assert kpis["orders"] == 1
    assert kpis["by_city"][0]["city"] == "Lahore"
    assert kpis["reviews"]["positive"] == 1
    assert kpis["potential_areas"][0]["city"] == "Lahore"
    assert CatalogProduct.objects.for_tenant(other_tenant).count() == 0


@pytest.mark.django_db
def test_reviews_api_lists_stored_reviews(api_client, user, tenant):
    apply_payload(
        tenant,
        "woocommerce",
        {
            "products": [{"external_id": "p1", "name": "Bar", "sku": "BAR", "unit_price": "10"}],
            "orders": [],
            "reviews": [{"external_id": "r1", "product_external_id": "p1", "rating": 5, "body": "Great", "reviewer": "Ayesha"}],
        },
    )
    api_client.force_authenticate(user=user)
    response = api_client.get("/api/v1/business/reviews/", HTTP_X_TENANT_ID=str(tenant.id))
    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["product_name"] == "Bar"
    assert response.data["results"][0]["sentiment"] == CommerceReview.Sentiment.POSITIVE


@pytest.mark.django_db
def test_promote_customers_copies_buyers_into_existing_leads(tenant):
    customer = CommerceCustomer.objects.create(tenant=tenant, name="Ayesha", email="ayesha@example.com", city="Lahore", source="shopify", external_id="c1")
    first = promote_customers_to_leads(tenant)
    assert first["created"] == 1
    second = promote_customers_to_leads(tenant)
    assert second["skipped"] == 1
    lead = Lead.objects.for_tenant(tenant).get()
    assert lead.company_name == "Ayesha"
    assert lead.email == customer.email
    assert lead.source == "shopify"
    assert "existing buyer" in lead.notes.lower()


@pytest.mark.django_db
def test_store_catalog_and_sync_api(api_client, user, tenant, monkeypatch):
    api_client.force_authenticate(user=user)
    headers = {"HTTP_X_TENANT_ID": str(tenant.id)}
    listed = api_client.get("/api/v1/business/stores/", **headers)
    assert listed.status_code == 200
    codes = {item["code"] for item in listed.data["items"]}
    assert {"shopify", "woocommerce", "etsy", "ebay"} <= codes
    saved = api_client.put(
        "/api/v1/business/stores/shopify/",
        {"shop_domain": "demo-shop.myshopify.com", "access_token": "shpat_test"},
        format="json",
        **headers,
    )
    assert saved.status_code == 200
    assert saved.data["credentials_configured"] is True
    assert "access_token" not in (saved.data.get("config") or {})

    def fake_fetch(provider, *, public, secret):
        assert provider == "shopify"
        assert secret.get("access_token") == "shpat_test"
        return {
            "products": [{"external_id": "11", "name": "Mug", "sku": "MUG", "unit_price": "20"}],
            "orders": [
                {
                    "external_id": "99",
                    "city": "Karachi",
                    "currency": "USD",
                    "status": "placed",
                    "customer": {"name": "Omar", "email": "omar@example.com", "city": "Karachi", "external_id": "5"},
                    "lines": [{"name": "Mug", "sku": "MUG", "quantity": 1, "unit_price": "20", "product_external_id": "11"}],
                }
            ],
            "reviews": [],
        }

    monkeypatch.setattr("apps.business.sync.fetch_store", fake_fetch)
    synced = api_client.post("/api/v1/business/stores/shopify/sync/", **headers)
    assert synced.status_code == 202
    assert synced.data["status"] == "COMPLETED"
    overview = api_client.get("/api/v1/business/overview/", **headers)
    assert overview.data["kpis"]["orders"] == 1
    assert overview.data["kpis"]["by_channel"][0]["channel"] == "shopify"
    assert overview.data["analysis"]["available"] is True
    assert overview.data["analysis"]["demand"]["served"][0]["city"] == "Karachi"
    assert synced.data["result"]["opportunities_created"] >= 1
    dashboard = api_client.get("/api/v1/dashboard/overview/", **headers)
    assert dashboard.status_code == 200
    assert dashboard.data["overview"]["commerce_orders"] == 1
    assert dashboard.data["overview"]["served_cities"] == 1
    insight = api_client.get("/api/v1/business/analyze/", **headers)
    assert insight.status_code == 200
    assert insight.data["analysis"]["available"] is True
    ran = api_client.post("/api/v1/business/analyze/", {}, format="json", **headers)
    assert ran.status_code == 202
    assert ran.data["job_type"] == "analyze_business"
    assert ran.data["status"] == "COMPLETED"


@pytest.mark.django_db
def test_store_sync_requires_credentials(api_client, user, tenant):
    api_client.force_authenticate(user=user)
    response = api_client.post("/api/v1/business/stores/etsy/sync/", HTTP_X_TENANT_ID=str(tenant.id))
    assert response.status_code == 400
    CRMConnection.objects.create(tenant=tenant, provider="etsy", status=CRMConnection.Status.CONFIGURED)
    empty = api_client.post("/api/v1/business/stores/etsy/sync/", HTTP_X_TENANT_ID=str(tenant.id))
    assert empty.status_code == 400


@pytest.mark.django_db
def test_commerce_analysis_served_vs_expansion_and_product_gaps(tenant):
    from apps.business.analysis import commerce_analysis, complete_analysis
    from apps.business.models import BusinessProfile
    from apps.opportunities.models import Opportunity

    profile = BusinessProfile.objects.create(tenant=tenant, current_market="Islamabad", industry="Food")
    apply_payload(
        tenant,
        "shopify",
        {
            "products": [
                {"external_id": "1", "name": "Mug", "sku": "MUG", "unit_price": "20"},
                {"external_id": "2", "name": "Bar", "sku": "BAR", "unit_price": "10"},
                {"external_id": "3", "name": "Tea", "sku": "TEA", "unit_price": "5"},
            ],
            "orders": [
                {
                    "external_id": "l1",
                    "city": "Lahore",
                    "status": "placed",
                    "currency": "PKR",
                    "customer": {"name": "A", "city": "Lahore", "external_id": "a"},
                    "lines": [{"name": "Mug", "sku": "MUG", "quantity": 1, "unit_price": "20", "product_external_id": "1"}],
                },
                {
                    "external_id": "l2",
                    "city": "Lahore",
                    "status": "placed",
                    "currency": "PKR",
                    "customer": {"name": "B", "city": "Lahore", "external_id": "b"},
                    "lines": [{"name": "Mug", "sku": "MUG", "quantity": 1, "unit_price": "20", "product_external_id": "1"}],
                },
                {
                    "external_id": "k1",
                    "city": "Karachi",
                    "status": "placed",
                    "currency": "PKR",
                    "customer": {"name": "C", "city": "Karachi", "external_id": "c"},
                    "lines": [{"name": "Bar", "sku": "BAR", "quantity": 1, "unit_price": "10", "product_external_id": "2"}],
                },
                {
                    "external_id": "k2",
                    "city": "Karachi",
                    "status": "placed",
                    "currency": "PKR",
                    "customer": {"name": "D", "city": "Karachi", "external_id": "d"},
                    "lines": [{"name": "Bar", "sku": "BAR", "quantity": 1, "unit_price": "10", "product_external_id": "2"}],
                },
            ],
            "reviews": [],
        },
    )
    analysis = commerce_analysis(tenant)
    served = {row["city"] for row in analysis["demand"]["served"]}
    assert served == {"Lahore", "Karachi"}
    expansion_cities = {row["city"] for row in analysis["demand"]["expansion"]}
    assert "Islamabad" in expansion_cities
    assert "Peshawar" not in expansion_cities
    gap_keys = {(row["name"], row["city"]) for row in analysis["products"]["gaps"]}
    assert ("Mug", "Karachi") in gap_keys
    assert ("Bar", "Lahore") in gap_keys
    unsold = {row["name"] for row in analysis["products"]["unsold"]}
    assert "Tea" in unsold
    summary = complete_analysis(tenant=tenant, user=None, run_ai=False)
    assert summary["opportunities_created"] >= 1
    titles = set(Opportunity.objects.for_tenant(tenant).values_list("title", flat=True))
    assert "Deepen coverage in Lahore" in titles
    assert "Investigate serving Islamabad" in titles
    assert "Offer Mug in Karachi" in titles
    profile.refresh_from_db()
    assert profile.last_expert.get("origin") == "heuristic"
    assert "invent" not in (profile.last_expert.get("recommendation") or "").lower()
