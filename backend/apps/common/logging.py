from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from apps.common.request_context import get_request_id, get_tenant_id


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": getattr(record, "service", "sipulse-api"),
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "") or get_request_id(),
            "tenant_id": getattr(record, "tenant_id", "") or get_tenant_id(),
            "job_id": getattr(record, "job_id", ""),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        record.tenant_id = get_tenant_id()
        return True
