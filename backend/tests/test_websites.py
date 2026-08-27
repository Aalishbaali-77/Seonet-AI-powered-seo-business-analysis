from __future__ import annotations

from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from apps.websites.models import Website


@pytest.mark.django_db
def test_viewer_cannot_create_website(viewer, tenant):
    client = APIClient()
    client.force_authenticate(user=viewer)
    with patch("apps.websites.serializers.validate_public_http_url", return_value="https://example.com"):
        response = client.post(
            "/api/v1/websites/",
            {"url": "https://example.com", "business_name": "Example"},
            format="json",
            HTTP_X_TENANT_ID=str(tenant.id),
        )
    assert response.status_code == 403


@pytest.mark.django_db
def test_owner_creates_website(api_client, user, tenant):
    api_client.force_authenticate(user=user)
    with patch("apps.websites.serializers.validate_public_http_url", return_value="https://example.com"):
        response = api_client.post(
            "/api/v1/websites/",
            {"url": "https://example.com", "business_name": "Example"},
            format="json",
            HTTP_X_TENANT_ID=str(tenant.id),
        )
    assert response.status_code == 201
    assert Website.objects.for_tenant(tenant).count() == 1
    website = Website.objects.for_tenant(tenant).get()
    with patch("apps.websites.serializers.validate_public_http_url", return_value="https://www.example.com/shop"):
        patched = api_client.patch(
            f"/api/v1/websites/{website.id}/",
            {"keywords": ["industrial pumps"], "url": "https://www.example.com/shop"},
            format="json",
            HTTP_X_TENANT_ID=str(tenant.id),
        )
    assert patched.status_code == 200
    website.refresh_from_db()
    assert website.keywords == ["industrial pumps"]
    assert website.domain == "www.example.com"


@pytest.mark.django_db
def test_tenant_isolation_websites(api_client, user, tenant, other_tenant):
    site = Website.objects.create(tenant=other_tenant, url="https://beta.example", domain="beta.example", name="Beta")
    api_client.force_authenticate(user=user)
    response = api_client.get(f"/api/v1/websites/{site.id}/", HTTP_X_TENANT_ID=str(tenant.id))
    assert response.status_code == 404
