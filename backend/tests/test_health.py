from __future__ import annotations


def test_live(api_client):
    response = api_client.get("/api/v1/health/live/")
    assert response.status_code == 200
    assert response.data["status"] == "ok"
    assert "X-Request-ID" in response


def test_ready(api_client, db):
    response = api_client.get("/api/v1/health/ready/")
    assert response.status_code == 200
    assert response.data["status"] == "ready"


def test_config_feature_flags(api_client, db):
    response = api_client.get("/api/v1/config/")
    assert response.status_code == 200
    assert response.data["product"] == "Seonet"
    assert response.data["branding"]["product_name"] == "Seonet"
    assert response.data["branding"]["primary_color"] == "#C2410C"
    assert "LEAD_DISCOVERY_ENABLED" in response.data["feature_flags"]
    assert response.data["landing"]["nav"]
    assert isinstance(response.data["packages"], list)
    assert isinstance(response.data["modules"], list)


def test_unauthenticated_error_envelope(api_client):
    response = api_client.get("/api/v1/auth/me/")
    assert response.status_code == 401
    assert response.data["error"]["code"] == "UNAUTHENTICATED"
    assert "request_id" in response.data["error"]
