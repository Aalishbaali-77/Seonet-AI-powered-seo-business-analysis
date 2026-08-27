from __future__ import annotations

import json
from typing import Any

import httpx

from providers.ai.base import AIProvider, CompletionResult, ProviderUnavailable

OPENAI_BASE = "https://api.openai.com/v1"
ANTHROPIC_BASE = "https://api.anthropic.com/v1"
XAI_BASE = "https://api.x.ai/v1"
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"


def _json_from_text(text: str) -> dict[str, Any]:
    payload = (text or "").strip()
    if not payload:
        return {}
    try:
        value = json.loads(payload)
        return value if isinstance(value, dict) else {"value": value}
    except json.JSONDecodeError:
        start = payload.find("{")
        end = payload.rfind("}")
        if start >= 0 and end > start:
            try:
                value = json.loads(payload[start : end + 1])
                if isinstance(value, dict):
                    return value
            except json.JSONDecodeError:
                pass
        return {"text": payload}


def _request(method: str, url: str, **kwargs) -> dict[str, Any]:
    with httpx.Client(timeout=30, follow_redirects=False) as client:
        response = client.request(method, url, **kwargs)
    if response.status_code >= 400:
        detail = ""
        try:
            body = response.json()
            detail = str(body.get("error", {}).get("message") or body.get("error") or body)[:240]
        except Exception:  # noqa: BLE001
            detail = (response.text or "")[:240]
        raise ProviderUnavailable(detail or f"{url} returned HTTP {response.status_code}.")
    return response.json()


def _result(data: dict[str, Any], prompt_tokens: int, completion_tokens: int, model: str) -> CompletionResult:
    return CompletionResult(
        data=data,
        prompt_tokens=int(prompt_tokens or 0),
        completion_tokens=int(completion_tokens or 0),
        model=str(model or ""),
    )


def _usage_openai(payload: dict[str, Any], fallback_model: str) -> tuple[int, int, str]:
    usage = payload.get("usage") or {}
    return (
        int(usage.get("prompt_tokens") or 0),
        int(usage.get("completion_tokens") or 0),
        str(payload.get("model") or fallback_model),
    )


def _usage_anthropic(payload: dict[str, Any], fallback_model: str) -> tuple[int, int, str]:
    usage = payload.get("usage") or {}
    return (
        int(usage.get("input_tokens") or 0),
        int(usage.get("output_tokens") or 0),
        str(payload.get("model") or fallback_model),
    )


def _usage_gemini(payload: dict[str, Any], fallback_model: str) -> tuple[int, int, str]:
    usage = payload.get("usageMetadata") or payload.get("usage_metadata") or {}
    return (
        int(usage.get("promptTokenCount") or usage.get("prompt_token_count") or 0),
        int(usage.get("candidatesTokenCount") or usage.get("candidates_token_count") or 0),
        fallback_model,
    )


class OpenAIAdapter(AIProvider):
    name = "openai"

    def __init__(self, api_key: str = "", model: str = ""):
        self.api_key = api_key
        self.model = model or "gpt-4o-mini"

    def probe(self) -> dict[str, Any]:
        if not self.api_key:
            raise ProviderUnavailable("OpenAI is not configured.")
        payload = _request("GET", f"{OPENAI_BASE}/models", headers={"Authorization": f"Bearer {self.api_key}"})
        count = len(payload.get("data") or [])
        return {"ok": True, "sample_count": count, "provider": self.name, "message": f"OpenAI accepted the key ({count} models visible)."}

    def complete(self, *, prompt: str, schema: dict[str, Any] | None = None) -> CompletionResult:
        if not self.api_key:
            raise ProviderUnavailable("OpenAI is not configured.")
        body: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }
        if schema is not None:
            body["response_format"] = {"type": "json_object"}
        payload = _request(
            "POST",
            f"{OPENAI_BASE}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json=body,
        )
        content = (((payload.get("choices") or [{}])[0].get("message") or {}).get("content")) or ""
        prompt_tokens, completion_tokens, model = _usage_openai(payload, self.model)
        return _result(_json_from_text(content), prompt_tokens, completion_tokens, model)


class AnthropicAdapter(AIProvider):
    name = "anthropic"

    def __init__(self, api_key: str = "", model: str = ""):
        self.api_key = api_key
        self.model = model or "claude-sonnet-4-5"

    def _headers(self) -> dict[str, str]:
        return {"x-api-key": self.api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}

    def probe(self) -> dict[str, Any]:
        if not self.api_key:
            raise ProviderUnavailable("Claude is not configured.")
        payload = _request("GET", f"{ANTHROPIC_BASE}/models", headers=self._headers())
        count = len(payload.get("data") or [])
        return {"ok": True, "sample_count": count, "provider": self.name, "message": f"Claude accepted the key ({count} models visible)."}

    def complete(self, *, prompt: str, schema: dict[str, Any] | None = None) -> CompletionResult:
        if not self.api_key:
            raise ProviderUnavailable("Claude is not configured.")
        body = {"model": self.model, "max_tokens": 1024, "messages": [{"role": "user", "content": prompt}]}
        payload = _request("POST", f"{ANTHROPIC_BASE}/messages", headers=self._headers(), json=body)
        parts = payload.get("content") or []
        content = "".join(str(item.get("text") or "") for item in parts if isinstance(item, dict))
        prompt_tokens, completion_tokens, model = _usage_anthropic(payload, self.model)
        return _result(_json_from_text(content), prompt_tokens, completion_tokens, model)


class XAIAdapter(AIProvider):
    name = "xai"

    def __init__(self, api_key: str = "", model: str = ""):
        self.api_key = api_key
        self.model = model or "grok-3-mini"

    def probe(self) -> dict[str, Any]:
        if not self.api_key:
            raise ProviderUnavailable("Grok is not configured.")
        payload = _request("GET", f"{XAI_BASE}/models", headers={"Authorization": f"Bearer {self.api_key}"})
        count = len(payload.get("data") or [])
        return {"ok": True, "sample_count": count, "provider": self.name, "message": f"Grok accepted the key ({count} models visible)."}

    def complete(self, *, prompt: str, schema: dict[str, Any] | None = None) -> CompletionResult:
        if not self.api_key:
            raise ProviderUnavailable("Grok is not configured.")
        body: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }
        payload = _request(
            "POST",
            f"{XAI_BASE}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json=body,
        )
        content = (((payload.get("choices") or [{}])[0].get("message") or {}).get("content")) or ""
        prompt_tokens, completion_tokens, model = _usage_openai(payload, self.model)
        return _result(_json_from_text(content), prompt_tokens, completion_tokens, model)


class GeminiAdapter(AIProvider):
    name = "google_gemini"

    def __init__(self, api_key: str = "", model: str = ""):
        self.api_key = api_key
        self.model = model or "gemini-2.0-flash"

    def probe(self) -> dict[str, Any]:
        if not self.api_key:
            raise ProviderUnavailable("Gemini is not configured.")
        payload = _request("GET", f"{GEMINI_BASE}/models", params={"key": self.api_key})
        count = len(payload.get("models") or [])
        return {"ok": True, "sample_count": count, "provider": self.name, "message": f"Gemini accepted the key ({count} models visible)."}

    def complete(self, *, prompt: str, schema: dict[str, Any] | None = None) -> CompletionResult:
        if not self.api_key:
            raise ProviderUnavailable("Gemini is not configured.")
        payload = _request(
            "POST",
            f"{GEMINI_BASE}/models/{self.model}:generateContent",
            params={"key": self.api_key},
            json={"contents": [{"parts": [{"text": prompt}]}]},
        )
        candidates = payload.get("candidates") or []
        parts = (((candidates[0] if candidates else {}).get("content") or {}).get("parts") or [])
        content = "".join(str(item.get("text") or "") for item in parts if isinstance(item, dict))
        prompt_tokens, completion_tokens, model = _usage_gemini(payload, self.model)
        return _result(_json_from_text(content), prompt_tokens, completion_tokens, model)


def provider_chain() -> list[AIProvider]:
    from apps.platform.lead_sources import resolve_ai_adapters

    return resolve_ai_adapters()
