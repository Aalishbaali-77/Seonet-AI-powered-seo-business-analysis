from __future__ import annotations

import contextvars
import uuid

_request_id: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")
_tenant_id: contextvars.ContextVar[str] = contextvars.ContextVar("tenant_id", default="")
_job_id: contextvars.ContextVar[str] = contextvars.ContextVar("job_id", default="")


def get_request_id() -> str:
    return _request_id.get() or ""


def set_request_id(value: str) -> None:
    _request_id.set(value)


def get_tenant_id() -> str:
    return _tenant_id.get() or ""


def set_tenant_id(value: str) -> None:
    _tenant_id.set(value)


def new_request_id() -> str:
    return f"req_{uuid.uuid4().hex[:20]}"
