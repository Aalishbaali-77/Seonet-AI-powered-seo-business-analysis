from __future__ import annotations

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.billing.entitlements import ensure_billing_catalog, tenant_module_codes
from apps.business.models import BusinessProfile, CatalogProduct, CommerceOrder, ImportBatch
from apps.markets.catalog import ensure_geo_catalog
from apps.markets.models import GeoPlace, MarketSignal
from apps.markets.scoring import DEFAULT_WEIGHTS, score_from_signals
from apps.opportunities.models import Opportunity


@pytest.mark.django_db
def test_scoring_does_not_invent_a_grade_without_signals():
    result = score_from_signals([], DEFAULT_WEIGHTS)
    assert result["score"] is None
    assert result["origin"] == "none"
    assert result["coverage"] == 0


@pytest.mark.django_db
def test_scoring_is_partial_when_some_signals_exist(tenant):
    ensure_geo_catalog()
    place = GeoPlace.objects.get(code="PK-PB-LHE")
    MarketSignal.objects.create(
        tenant=tenant,
        place=place,
        kind=MarketSignal.Kind.DEMAND,
        value=90,
        source="operator ingest",
        verification_status=MarketSignal.Verification.UNVERIFIED,
    )
    result = score_from_signals(MarketSignal.objects.for_tenant(tenant).filter(place=place), DEFAULT_WEIGHTS)
    assert result["score"] is not None
    assert result["origin"] == "estimated"
    assert "demand" not in result["missing"]
    assert "population" in result["missing"]


@pytest.mark.django_db
def test_business_and_market_apis_are_tenant_scoped(api_client, user, tenant, other_tenant, other_user):
    ensure_billing_catalog()
    api_client.force_authenticate(user=user)
    overview = api_client.get("/api/v1/business/overview/", HTTP_X_TENANT_ID=str(tenant.id))
    assert overview.status_code == 200
    assert overview.data["kpis"]["available"] is False
    saved = api_client.patch(
        "/api/v1/business/profile/",
        {"industry": "Food & Beverage", "category": "Chocolate", "current_market": "Karachi", "business_type": "ecommerce"},
        format="json",
        HTTP_X_TENANT_ID=str(tenant.id),
    )
    assert saved.status_code == 200
    assert saved.data["industry"] == "Food & Beverage"
    assert BusinessProfile.objects.for_tenant(tenant).count() == 1

    markets = api_client.get("/api/v1/markets/overview/", HTTP_X_TENANT_ID=str(tenant.id))
    assert markets.status_code == 200
    assert markets.data["scored_cities"] == 0
    assert all(row["score"]["score"] is None for row in markets.data["cities"])

    api_client.force_authenticate(user=other_user)
    blocked = api_client.get("/api/v1/business/overview/", HTTP_X_TENANT_ID=str(other_tenant.id))
    assert blocked.status_code == 200
    assert blocked.data["profile"]["industry"] == ""


@pytest.mark.django_db
def test_opportunity_and_product_import_stay_on_tenant(api_client, user, tenant, other_tenant, other_user):
    ensure_billing_catalog()
    api_client.force_authenticate(user=user)
    created = api_client.post(
        "/api/v1/opportunities/",
        {
            "title": "Test Lahore gifting expansion",
            "type": "geographic",
            "evidence": "No commerce data yet; this is a user-recorded hypothesis.",
            "recommended_action": "Import orders, then re-evaluate.",
        },
        format="json",
        HTTP_X_TENANT_ID=str(tenant.id),
    )
    assert created.status_code == 201
    csv_body = SimpleUploadedFile("products.csv", b"name,sku,category,unit_price\nDark bar,CHOC-1,Chocolate,450\n", content_type="text/csv")
    upload = api_client.post(
        "/api/v1/business/import/",
        {"kind": "products", "file": csv_body},
        format="multipart",
        HTTP_X_TENANT_ID=str(tenant.id),
    )
    assert upload.status_code == 202
    assert upload.data["result"]["created"] == 1
    assert CatalogProduct.objects.for_tenant(tenant).count() == 1
    api_client.force_authenticate(user=other_user)
    listed = api_client.get("/api/v1/opportunities/", HTTP_X_TENANT_ID=str(other_tenant.id))
    assert listed.status_code == 200
    assert listed.data["results"] == []
    assert Opportunity.objects.for_tenant(other_tenant).count() == 0
    assert CatalogProduct.objects.for_tenant(other_tenant).count() == 0


@pytest.mark.django_db
def test_csv_template_download_then_import(api_client, user, tenant):
    from apps.business.imports import CSV_TEMPLATES
    from apps.business.models import CommerceOrder

    api_client.force_authenticate(user=user)
    headers = {"HTTP_X_TENANT_ID": str(tenant.id)}
    products = api_client.get("/api/v1/business/import/?kind=products", **headers)
    assert products.status_code == 200
    assert products["Content-Type"].startswith("text/csv")
    assert "sipulse-products-template.csv" in products["Content-Disposition"]
    product_text = products.content.decode("utf-8-sig")
    assert product_text.splitlines()[0] == ",".join(CSV_TEMPLATES["products"]["columns"])
    filled_products = SimpleUploadedFile(
        "products.csv",
        (product_text.strip() + "\nDark bar,CHOC-1,Chocolate,450,200\n").encode("utf-8"),
        content_type="text/csv",
    )
    uploaded_products = api_client.post(
        "/api/v1/business/import/",
        {"kind": "products", "file": filled_products},
        format="multipart",
        **headers,
    )
    assert uploaded_products.status_code == 202
    assert uploaded_products.data["result"]["created"] == 1
    assert CatalogProduct.objects.for_tenant(tenant).filter(sku="CHOC-1").exists()

    semicolon = SimpleUploadedFile(
        "products.csv",
        "name;sku;category;unit_price;cost_price\nMilk;MLK-1;Dairy;120;60\n".encode("utf-8"),
        content_type="text/csv",
    )
    semi = api_client.post("/api/v1/business/import/", {"kind": "products", "file": semicolon}, format="multipart", **headers)
    assert semi.status_code == 202
    assert semi.data["result"]["created"] == 1
    assert CatalogProduct.objects.for_tenant(tenant).filter(sku="MLK-1").exists()

    utf16 = SimpleUploadedFile(
        "products.csv",
        "\ufeffname,sku,category,unit_price,cost_price\nTea,TEA-1,Drinks,80,30\n".encode("utf-16"),
        content_type="text/csv",
    )
    wide = api_client.post("/api/v1/business/import/", {"kind": "products", "file": utf16}, format="multipart", **headers)
    assert wide.status_code == 202
    assert wide.data["result"]["created"] == 1
    assert CatalogProduct.objects.for_tenant(tenant).filter(sku="TEA-1").exists()

    orders = api_client.get("/api/v1/business/import/?kind=orders", **headers)
    assert orders.status_code == 200
    order_text = orders.content.decode("utf-8-sig")
    assert order_text.splitlines()[0] == ",".join(CSV_TEMPLATES["orders"]["columns"])
    filled_orders = SimpleUploadedFile(
        "orders.csv",
        (order_text.strip() + "\nORD-1,2026-01-02T10:00:00Z,Ayesha,ayesha@example.com,Lahore,csv,PKR,CHOC-1,Dark bar,2,450,0,200\n").encode("utf-8"),
        content_type="text/csv",
    )
    uploaded_orders = api_client.post(
        "/api/v1/business/import/",
        {"kind": "orders", "file": filled_orders},
        format="multipart",
        **headers,
    )
    assert uploaded_orders.status_code == 202
    assert uploaded_orders.data["result"]["created"] == 1
    assert CommerceOrder.objects.for_tenant(tenant).filter(external_id="ORD-1").exists()
    unknown = api_client.get("/api/v1/business/import/?kind=leads", **headers)
    assert unknown.status_code == 400


@pytest.mark.django_db
def test_orders_csv_import_creates_linked_import_batch(api_client, user, tenant):
    api_client.force_authenticate(user=user)
    headers = {"HTTP_X_TENANT_ID": str(tenant.id)}
    csv_bytes = (
        "order_id,ordered_at,customer_name,email,city,channel,currency,sku,product_name,quantity,unit_price,discount,cost\n"
        "ORD-100,2026-01-02T10:00:00Z,Ayesha,ayesha@example.com,Lahore,csv,PKR,CHOC-1,Dark bar,2,450,0,200\n"
    ).encode("utf-8")

    resp = api_client.post(
        "/api/v1/business/import/",
        {"kind": "orders", "file": SimpleUploadedFile("first-batch.csv", csv_bytes, content_type="text/csv")},
        format="multipart",
        **headers,
    )
    assert resp.status_code == 202
    assert resp.data["result"]["created"] == 1

    batches = list(ImportBatch.objects.for_tenant(tenant))
    assert len(batches) == 1
    batch = batches[0]
    assert batch.file_name == "first-batch.csv"
    assert batch.kind == ImportBatch.Kind.ORDERS
    assert batch.status == ImportBatch.Status.SUCCESS
    assert batch.rows_total == 1
    assert batch.rows_imported == 1

    order = CommerceOrder.objects.for_tenant(tenant).get(external_id="ORD-100")
    assert order.import_batch_id == batch.id


@pytest.mark.django_db
def test_duplicate_orders_csv_import_does_not_create_duplicate_orders(api_client, user, tenant):
    api_client.force_authenticate(user=user)
    headers = {"HTTP_X_TENANT_ID": str(tenant.id)}
    csv_bytes = (
        "order_id,ordered_at,customer_name,email,city,channel,currency,sku,product_name,quantity,unit_price,discount,cost\n"
        "ORD-200,2026-01-02T10:00:00Z,Ayesha,ayesha@example.com,Lahore,csv,PKR,CHOC-1,Dark bar,2,450,0,200\n"
    ).encode("utf-8")

    first = api_client.post(
        "/api/v1/business/import/",
        {"kind": "orders", "file": SimpleUploadedFile("orders.csv", csv_bytes, content_type="text/csv")},
        format="multipart",
        **headers,
    )
    assert first.status_code == 202
    assert first.data["result"]["created"] == 1
    assert CommerceOrder.objects.for_tenant(tenant).filter(external_id="ORD-200").count() == 1

    # Re-import the exact same file — the duplicate order_id must be skipped, not recreated.
    second = api_client.post(
        "/api/v1/business/import/",
        {"kind": "orders", "file": SimpleUploadedFile("orders.csv", csv_bytes, content_type="text/csv")},
        format="multipart",
        **headers,
    )
    assert second.status_code == 202
    assert second.data["result"]["created"] == 0
    assert second.data["result"]["duplicates"] == 1
    assert second.data["result"]["skipped"] == 1

    assert CommerceOrder.objects.for_tenant(tenant).filter(external_id="ORD-200").count() == 1

    second_batch = ImportBatch.objects.for_tenant(tenant).order_by("-created_at").first()
    assert second_batch.status == ImportBatch.Status.FAILED
    assert second_batch.rows_total == 1
    assert second_batch.rows_imported == 0


@pytest.mark.django_db
def test_starter_plan_includes_growth_modules(user):
    from apps.billing.entitlements import apply_plan_to_tenant, ensure_billing_catalog, tenant_module_codes
    from apps.billing.models import Plan
    from apps.rbac.services import assign_role, provision_tenant_roles
    from apps.tenants.models import Membership, Tenant

    ensure_billing_catalog()
    tenant = Tenant.objects.create(name="Starter Co", slug="starter-co", status=Tenant.Status.ACTIVE)
    provision_tenant_roles(tenant)
    membership = Membership.objects.create(tenant=tenant, user=user, is_default=True, status=Membership.Status.ACTIVE)
    assign_role(membership, "owner")
    apply_plan_to_tenant(tenant, Plan.objects.get(code="starter"), status="trialing")
    codes = tenant_module_codes(tenant)
    assert {"websites", "audits", "business", "markets", "opportunities"} <= codes
    assert "leads" not in codes
    assert "marketing" not in codes


@pytest.mark.django_db
def test_starter_cannot_use_marketing_api(api_client, user):
    from apps.billing.entitlements import apply_plan_to_tenant, ensure_billing_catalog
    from apps.billing.models import Plan
    from apps.rbac.services import assign_role, provision_tenant_roles
    from apps.tenants.models import Membership, Tenant

    ensure_billing_catalog()
    tenant = Tenant.objects.create(name="Lite", slug="lite", status=Tenant.Status.ACTIVE)
    provision_tenant_roles(tenant)
    membership = Membership.objects.create(tenant=tenant, user=user, is_default=True, status=Membership.Status.ACTIVE)
    assign_role(membership, "owner")
    apply_plan_to_tenant(tenant, Plan.objects.get(code="starter"), status="trialing")
    api_client.force_authenticate(user=user)
    response = api_client.post(
        "/api/v1/marketing/campaigns/",
        {"name": "Blocked", "audience_type": "lead_list", "channel": "offer"},
        format="json",
        HTTP_X_TENANT_ID=str(tenant.id),
    )
    assert response.status_code == 403
    assert response.data["error"]["code"] == "FEATURE_DISABLED"


@pytest.mark.django_db
def test_market_brief_stays_empty_without_signals_or_orders(api_client, user, tenant):
    api_client.force_authenticate(user=user)
    headers = {"HTTP_X_TENANT_ID": str(tenant.id)}
    brief = api_client.get("/api/v1/markets/brief/", **headers)
    assert brief.status_code == 200
    assert brief.data["available"] is False
    assert brief.data["scored"] == []
    assert brief.data["signal_count"] == 0
    asked = api_client.post("/api/v1/markets/brief/", {"question": "Where should we expand?"}, format="json", **headers)
    assert asked.status_code == 202
    assert asked.data["job_type"] == "analyze_market"
    assert asked.data["status"] == "COMPLETED"
    assert asked.data["result"]["origin"] == "facts_only"
    assert asked.data["result"]["inference"] == ""
    assert "Enable the AI module" in asked.data["result"]["recommendation"]
    assert asked.data["result"]["stage"] == "Completed"


@pytest.mark.django_db
def test_market_brief_analyzes_saved_business_input(api_client, user, tenant):
    api_client.force_authenticate(user=user)
    headers = {"HTTP_X_TENANT_ID": str(tenant.id)}
    analyzed = api_client.post(
        "/api/v1/markets/brief/",
        {
            "question": "",
            "profile": {
                "industry": "Food & Beverage",
                "category": "Chocolate",
                "current_market": "Karachi",
                "goal": "Grow gifting in Pakistan",
                "business_type": "ecommerce",
            },
        },
        format="json",
        **headers,
    )
    assert analyzed.status_code == 202
    assert analyzed.data["job_type"] == "analyze_market"
    assert analyzed.data["status"] == "COMPLETED"
    assert any("Chocolate" in line or "Food" in line for line in analyzed.data["result"]["findings"])
    assert analyzed.data["result"]["inference"] == ""
    brief = api_client.get("/api/v1/markets/brief/", **headers)
    assert brief.status_code == 200
    assert brief.data["available"] is True
    assert brief.data["profile"]["industry"] == "Food & Beverage"
    assert brief.data["profile"]["current_market"] == "Karachi"
    assert brief.data["last_analysis"]["origin"] == "facts_only"
    asked = api_client.post(
        "/api/v1/ai/query/",
        {"question": "Analyze the market for my business"},
        format="json",
        **headers,
    )
    assert asked.status_code == 200
    assert asked.data["intent"] == "market_analysis"
    assert asked.data["href"] == "/app/markets"
    assert asked.data["job_id"]
    assert any("Karachi" in line or "Chocolate" in line or "Food" in line for line in asked.data["facts"])
    assert asked.data["recommendation"]


@pytest.mark.django_db
def test_market_signal_csv_and_brief_cite_served_overlap(api_client, user, tenant, other_user, other_tenant):
    from apps.business.models import CommerceOrder, CommerceOrderItem
    from apps.markets.imports import CSV_COLUMNS

    api_client.force_authenticate(user=user)
    headers = {"HTTP_X_TENANT_ID": str(tenant.id)}
    template = api_client.get("/api/v1/markets/import/", **headers)
    assert template.status_code == 200
    assert template["Content-Type"].startswith("text/csv")
    header = template.content.decode("utf-8-sig").splitlines()[0]
    assert header == ",".join(CSV_COLUMNS)
    filled = SimpleUploadedFile(
        "signals.csv",
        (header + "\nLahore,demand,80,operator ingest,\nKarachi,demand,70,operator ingest,\n").encode("utf-8"),
        content_type="text/csv",
    )
    uploaded = api_client.post("/api/v1/markets/import/", {"file": filled}, format="multipart", **headers)
    assert uploaded.status_code == 202
    assert uploaded.data["result"]["created"] == 2
    assert MarketSignal.objects.for_tenant(tenant).count() == 2

    order = CommerceOrder.objects.create(tenant=tenant, city="Lahore", status=CommerceOrder.Status.PLACED, source="csv")
    CommerceOrderItem.objects.create(tenant=tenant, order=order, name="Bar", quantity=1, unit_price="100")

    brief = api_client.get("/api/v1/markets/brief/", **headers)
    assert brief.status_code == 200
    assert brief.data["available"] is True
    assert {row["name"] for row in brief.data["scored"]} == {"Lahore", "Karachi"}
    assert [row["name"] for row in brief.data["overlap"]] == ["Lahore"]
    assert [row["name"] for row in brief.data["signal_without_orders"]] == ["Karachi"]
    texts = " ".join(item["text"] for item in brief.data["citations"])
    assert "Lahore" in texts
    asked = api_client.post("/api/v1/markets/brief/", {"question": "Which scored cities have no orders?"}, format="json", **headers)
    assert asked.status_code == 202
    assert asked.data["status"] == "COMPLETED"
    assert any("Karachi" in item["text"] for item in asked.data["result"]["citations"])

    api_client.force_authenticate(user=other_user)
    other = api_client.get("/api/v1/markets/brief/", HTTP_X_TENANT_ID=str(other_tenant.id))
    assert other.status_code == 200
    assert other.data["signal_count"] == 0
    assert other.data["scored"] == []
    assert other.data["last_analysis"] is None


@pytest.mark.django_db
def test_collect_markets_uses_open_data_and_lead_sources(api_client, user, tenant, other_user, other_tenant, monkeypatch):
    ensure_geo_catalog()
    lahore = GeoPlace.objects.get(code="PK-PB-LHE")
    karachi = GeoPlace.objects.get(code="PK-SD-KHI")
    monkeypatch.setattr(
        "apps.markets.collect.collect_wikidata_population",
        lambda: [(lahore, 11_000_000), (karachi, 16_000_000)],
    )
    monkeypatch.setattr(
        "apps.markets.collect.collect_overpass_shops",
        lambda term: [(lahore, 40), (karachi, 80)],
    )
    monkeypatch.setattr(
        "apps.markets.collect.collect_adapter_counts",
        lambda tenant, term: {"google_places": [(lahore, 10), (karachi, 20)]},
    )
    api_client.force_authenticate(user=user)
    headers = {"HTTP_X_TENANT_ID": str(tenant.id)}
    ran = api_client.post("/api/v1/markets/collect/", {}, format="json", **headers)
    assert ran.status_code == 202
    assert ran.data["status"] == "COMPLETED"
    assert ran.data["job_type"] == "collect_markets"
    rows = list(MarketSignal.objects.for_tenant(tenant))
    assert len(rows) == 6
    assert {item.verification_status for item in rows} == {MarketSignal.Verification.ESTIMATED}
    karachi_pop = MarketSignal.objects.for_tenant(tenant).get(place=karachi, kind=MarketSignal.Kind.POPULATION)
    assert karachi_pop.value == 100
    karachi_shops = MarketSignal.objects.for_tenant(tenant).get(place=karachi, kind=MarketSignal.Kind.BUSINESS_DENSITY, source_provider="overpass")
    assert karachi_shops.value == 100
    api_client.force_authenticate(user=other_user)
    assert MarketSignal.objects.for_tenant(other_tenant).count() == 0


@pytest.mark.django_db
def test_collect_markets_stays_empty_when_sources_return_nothing(api_client, user, tenant, monkeypatch):
    monkeypatch.setattr("apps.markets.collect.collect_wikidata_population", lambda: [])
    monkeypatch.setattr("apps.markets.collect.collect_overpass_shops", lambda term: [])
    monkeypatch.setattr("apps.markets.collect.collect_adapter_counts", lambda tenant, term: {})
    api_client.force_authenticate(user=user)
    ran = api_client.post("/api/v1/markets/collect/", {}, format="json", HTTP_X_TENANT_ID=str(tenant.id))
    assert ran.status_code == 202
    assert ran.data["status"] == "FAILED"
    assert MarketSignal.objects.for_tenant(tenant).count() == 0
