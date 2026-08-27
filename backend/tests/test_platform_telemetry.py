from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from rest_framework.test import APIClient

from apps.ai.models import AIRequest, AskQuery
from apps.auditlog.models import PageView
from apps.platform.lead_sources import ensure_lead_sources
from apps.platform.models import LeadSource
from apps.users.models import User
from services.ai_gateway import AIService


@pytest.mark.django_db
def test_prompts_asks_and_pages_are_visible_to_platform_owner(api_client, user, tenant, other_user, other_tenant):
    ensure_lead_sources()
    source = LeadSource.objects.get(code="anthropic")
    source.encrypted_config = {"api_key": "sk-ant-test"}
    source.is_enabled = True
    source.save()
    mock_response = MagicMock(status_code=200)
    mock_response.json.return_value = {
        "model": "claude-sonnet-4-5",
        "content": [{"type": "text", "text": '{"industry":"dental"}'}],
        "usage": {"input_tokens": 8, "output_tokens": 4},
    }
    with patch("providers.ai.adapters.httpx.Client") as client_cls:
        client_cls.return_value.__enter__.return_value.request.return_value = mock_response
        AIService.complete(tenant=tenant, user=user, task="icp_parse", prompt="Parse this ICP", untrusted="dental in Karachi")

    api_client.force_authenticate(user=user)
    asked = api_client.post(
        "/api/v1/ai/query/",
        {"question": "How many leads are in this workspace?"},
        format="json",
        HTTP_X_TENANT_ID=str(tenant.id),
    )
    assert asked.status_code == 200
    viewed = api_client.post(
        "/api/v1/telemetry/page/",
        {"path": "/app/leads", "title": "Leads"},
        format="json",
        HTTP_X_TENANT_ID=str(tenant.id),
    )
    assert viewed.status_code == 201
    PageView.objects.create(tenant=other_tenant, user=other_user, path="/app/crm")

    forbidden = api_client.get("/api/v1/platform/telemetry/prompts/")
    assert forbidden.status_code == 403

    admin = User.objects.create_superuser(email="owner@platform.test", password="SecurePass!123")
    owner = APIClient()
    owner.force_authenticate(user=admin)
    prompts = owner.get("/api/v1/platform/telemetry/prompts/")
    assert prompts.status_code == 200
    assert prompts.data["count"] >= 1
    row = prompts.data["results"][0]
    assert row["tenant_name"] == tenant.name
    assert "Parse this ICP" in row["prompt"]
    assert "dental in Karachi" in row["untrusted_input"]
    asks = owner.get("/api/v1/platform/telemetry/asks/")
    assert asks.data["count"] >= 1
    assert any("How many leads" in item["question"] for item in asks.data["results"])
    pages = owner.get("/api/v1/platform/telemetry/pages/")
    paths = {item["path"] for item in pages.data["results"]}
    assert "/app/leads" in paths
    assert "/app/crm" in paths
    filtered = owner.get(f"/api/v1/platform/telemetry/pages/?tenant_id={other_tenant.id}")
    assert filtered.data["count"] == 1
    assert filtered.data["results"][0]["path"] == "/app/crm"
    assert AIRequest.objects.for_tenant(tenant).get().prompt
    assert AskQuery.objects.for_tenant(tenant).count() == 1
