from __future__ import annotations

import pytest

from apps.ai.models import AIRequest
from apps.billing.entitlements import apply_plan_to_tenant
from apps.billing.models import Plan
from apps.common.exceptions import APIError
from apps.websites.keywords import collect_keywords, draft_keyword_suggestions, suggest_keywords
from apps.websites.models import KeywordRankRun, Website
from apps.websites.serp import _cse_id, lookup_keyword


@pytest.mark.django_db
def test_collect_and_suggest_from_stored_keywords(tenant):
    website = Website.objects.create(
        tenant=tenant,
        url="https://acme.test",
        domain="acme.test",
        name="Acme",
        keywords=["industrial pumps"],
        target_markets=["Karachi"],
    )
    keywords = collect_keywords(website)
    assert "industrial pumps" in keywords
    assert any("Karachi" in item for item in keywords)
    suggestions = suggest_keywords(website, keywords)
    assert any(item["origin"] == "recommendation" for item in suggestions)
    assert all("page one" not in item["why"].lower() or "not" in item["why"].lower() for item in suggestions)


@pytest.mark.django_db
def test_lookup_marks_first_page_from_licensed_sample(monkeypatch):
    monkeypatch.setattr(
        "apps.websites.serp._google_cse",
        lambda query, api_key, cx: [
            {"position": 1, "url": "https://other.test/", "title": "Other", "host": "other.test"},
            {"position": 3, "url": "https://www.acme.test/pumps", "title": "Pumps", "host": "acme.test"},
        ],
    )
    row = lookup_keyword(query="industrial pumps", domain="acme.test", provider="google_custom_search", api_key="k", cx="cx")
    assert row["position"] == 3
    assert row["in_first_page"] is True
    assert row["origin"] == "fact"


@pytest.mark.django_db
def test_lookup_does_not_treat_similar_host_as_this_domain(monkeypatch):
    monkeypatch.setattr(
        "apps.websites.serp._google_cse",
        lambda query, api_key, cx: [
            {"position": 2, "url": "https://notacme.test/", "title": "Other", "host": "notacme.test"},
        ],
    )
    miss = lookup_keyword(query="industrial pumps", domain="acme.test", provider="google_custom_search", api_key="k", cx="cx")
    assert miss["position"] is None
    assert miss["in_first_page"] is False


def test_cse_id_accepts_engine_id_or_cx_query():
    assert _cse_id("abc123") == "abc123"
    assert _cse_id("https://cse.google.com/cse?cx=abc123&hl=en") == "abc123"
    assert _cse_id("https://www.google.com/search?q=pumps") == ""


@pytest.mark.django_db
def test_keyword_job_progress_without_serp_key(api_client, user, tenant, other_user, other_tenant):
    website = Website.objects.create(
        tenant=tenant,
        url="https://acme.test",
        domain="acme.test",
        keywords=["industrial pumps"],
    )
    api_client.force_authenticate(user=user)
    headers = {"HTTP_X_TENANT_ID": str(tenant.id)}
    started = api_client.post(f"/api/v1/websites/{website.id}/keywords/", **headers)
    assert started.status_code == 202
    assert started.data["job_type"] == "check_keyword_ranks"
    assert started.data["status"] == "COMPLETED"
    assert started.data["result"]["stage"] == "Completed"
    listed = api_client.get(f"/api/v1/websites/{website.id}/keywords/", **headers)
    assert listed.status_code == 200
    run = listed.data["run"]
    assert run["results"][0]["keyword"] == "industrial pumps"
    assert run["results"][0]["position"] is None
    assert "Custom Search" in run["results"][0]["error"] or "SerpAPI" in run["results"][0]["error"]
    assert run["suggestions"]
    assert run["ai"]["used"] is False
    assert "Scale" in run["ai"]["reason"]
    api_client.force_authenticate(user=other_user)
    other = api_client.get(f"/api/v1/websites/{website.id}/keywords/", HTTP_X_TENANT_ID=str(other_tenant.id))
    assert other.status_code == 404
    assert KeywordRankRun.objects.for_tenant(other_tenant).count() == 0


@pytest.mark.django_db
def test_scale_package_uses_claude_for_business_keywords(tenant, user, monkeypatch):
    apply_plan_to_tenant(tenant, Plan.objects.get(code="scale"), status="active")
    website = Website.objects.create(
        tenant=tenant,
        url="https://acme.test",
        domain="acme.test",
        industry="industrial equipment",
        keywords=["industrial pumps"],
        target_markets=["Karachi"],
    )

    def fake_complete(*, tenant, user, task, prompt, untrusted="", schema=None):
        assert task == "keyword_suggestions"
        assert "industrial pumps" in untrusted
        AIRequest.objects.create(
            tenant=tenant,
            user=user,
            provider="anthropic",
            model="claude-sonnet-4-5",
            task=task,
            status="completed",
            prompt_tokens=20,
            completion_tokens=10,
        )
        return {
            "suggestions": [
                {
                    "keyword": "what is a centrifugal pump",
                    "intent": "aeo",
                    "why": "Question form grounded in the stored pumps keyword.",
                }
            ]
        }

    monkeypatch.setattr("apps.websites.keywords.AIService.complete", fake_complete)
    suggestions, ai = draft_keyword_suggestions(website, ["industrial pumps"], user=user)
    assert ai["used"] is True
    assert ai["provider"] == "anthropic"
    assert "Claude" in ai["reason"]
    assert any(item["keyword"] == "what is a centrifugal pump" and item["origin"] == "inference" for item in suggestions)


@pytest.mark.django_db
def test_scale_package_skips_ai_when_credits_exhausted(tenant, user, monkeypatch):
    apply_plan_to_tenant(tenant, Plan.objects.get(code="scale"), status="active")
    website = Website.objects.create(
        tenant=tenant,
        url="https://acme.test",
        domain="acme.test",
        keywords=["industrial pumps"],
    )

    def fake_complete(**_kwargs):
        raise APIError(
            "This workspace has used its package AI credits for the current billing period. Upgrade the package or wait until the period resets.",
            code="QUOTA_EXCEEDED",
            status_code=402,
        )

    monkeypatch.setattr("apps.websites.keywords.AIService.complete", fake_complete)
    suggestions, ai = draft_keyword_suggestions(website, ["industrial pumps"], user=user)
    assert ai["used"] is False
    assert "credits" in ai["reason"].lower()
    assert suggestions
