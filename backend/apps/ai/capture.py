from __future__ import annotations

import json
from typing import Any


PROMPT_LIMIT = 12000
RESPONSE_LIMIT = 8000
QUESTION_LIMIT = 4000


def clip(value: Any, limit: int) -> str:
    text = value if isinstance(value, str) else json.dumps(value, default=str) if value is not None else ""
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def client_ip(request) -> str | None:
    if request is None:
        return None
    ip = request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR"))
    if ip and "," in ip:
        ip = ip.split(",")[0].strip()
    return ip or None
