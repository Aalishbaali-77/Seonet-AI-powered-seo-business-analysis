from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from apps.ai.credits import credits_used
from apps.ai.models import AIRequest
from apps.billing.entitlements import apply_plan_to_tenant
from apps.billing.models import Plan
from apps.platform.lead_sources import ensure_lead_sources
from apps.platform.models import LeadSource
from apps.usage.models import UsageRecord
from services.ai_gateway import AIService


def _enable_claude():
    ensure_lead_sources()
    source = LeadSource.objects.get(code="anthropic")
    source.encrypted_config = {"api_key": "sk-ant-test"}
    source.is_enabled = True
    source.save()
    return source


def _claude_payload(*, input_tokens=40, output_tokens=12):
    mock_response = MagicMock(status_code=200)
    mock_response.json.return_value = {
        "model": "claude-sonnet-4-5",
        "content": [{"type": "text", "text": '{"industry":"dental services","locations":["Karachi"],"keywords":["clinic"]}'}],
        "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
    }
    return mock_response


@pytest.mark.django_db
def test_platform_claude_key_serves_any_tenant(tenant, other_tenant, user, other_user):
    _enable_claude()
    mock_response = _claude_payload()
    with patch("providers.ai.adapters.httpx.Client") as client_cls:
        client_cls.return_value.__enter__.return_value.request.return_value = mock_response
        first = AIService.complete(tenant=tenant, user=user, task="icp_parse", prompt="hello", schema={"type": "object"})
        second = AIService.complete(tenant=other_tenant, user=other_user, task="icp_parse", prompt="hello", schema={"type": "object"})
    assert first["industry"] == "dental services"
    assert second["industry"] == "dental services"
    assert AIRequest.objects.for_tenant(tenant).count() == 1
    assert AIRequest.objects.for_tenant(other_tenant).count() == 1
    acme = AIRequest.objects.for_tenant(tenant).get()
    assert acme.provider == "anthropic"
    assert acme.prompt_tokens == 40
    assert acme.completion_tokens == 12
    assert credits_used(tenant) == 52
    assert credits_used(other_tenant) == 52
    assert UsageRecord.objects.for_tenant(tenant).filter(event_type="ai_tokens", quantity=52).exists()


@pytest.mark.django_db
def test_package_ai_credits_are_enforced(tenant, user):
    apply_plan_to_tenant(tenant, Plan.objects.get(code="growth"), status="active")
    plan = Plan.objects.get(code="growth")
    plan.ai_credits = 50
    plan.save(update_fields=["ai_credits"])
    _enable_claude()
    mock_response = _claude_payload(input_tokens=40, output_tokens=12)
    with patch("providers.ai.adapters.httpx.Client") as client_cls:
        client_cls.return_value.__enter__.return_value.request.return_value = mock_response
        AIService.complete(tenant=tenant, user=user, task="advisor", prompt="facts")
        with pytest.raises(Exception) as exc:
            AIService.complete(tenant=tenant, user=user, task="advisor", prompt="facts")
    assert getattr(exc.value, "error_code", "") == "QUOTA_EXCEEDED"
    assert AIRequest.objects.for_tenant(tenant).filter(status="completed").count() == 1


@pytest.mark.django_db
def test_tenant_usage_endpoint_reports_credits(api_client, tenant, user):
    _enable_claude()
    mock_response = _claude_payload()
    with patch("providers.ai.adapters.httpx.Client") as client_cls:
        client_cls.return_value.__enter__.return_value.request.return_value = mock_response
        AIService.complete(tenant=tenant, user=user, task="icp_parse", prompt="hello")
    api_client.force_authenticate(user=user)
    response = api_client.get("/api/v1/ai/usage/", HTTP_X_TENANT_ID=str(tenant.id))
    assert response.status_code == 200
    assert response.data["credits_used"] == 52
    assert response.data["credits_limit"] == Plan.objects.get(code="growth").ai_credits
    assert response.data["tokens"] == 52
    assert response.data["requests"] == 1
