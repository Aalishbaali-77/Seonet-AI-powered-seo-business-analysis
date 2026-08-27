from __future__ import annotations

from typing import Any

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError, Throttled
from rest_framework.views import exception_handler

from apps.common.request_context import get_request_id


class APIError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "API_ERROR"
    default_detail = "Request failed."

    def __init__(self, message: str | None = None, code: str | None = None, details: Any = None, status_code: int | None = None):
        self.details_payload = details or {}
        self.error_code = code or self.default_code
        if status_code:
            self.status_code = status_code
        super().__init__(detail=message or self.default_detail, code=self.error_code)


class FeatureDisabled(APIError):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = "FEATURE_DISABLED"
    default_detail = "This feature is not enabled."


class TenantRequired(APIError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "TENANT_REQUIRED"
    default_detail = "A tenant context is required."


def _error_payload(code: str, message: str, details: Any = None) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
            "request_id": get_request_id(),
        }
    }


def api_exception_handler(exc, context):
    request = context.get("request")
    if request is not None and not getattr(request, "request_id", None):
        pass

    if isinstance(exc, APIError):
        return _response(exc.status_code, exc.error_code, str(exc.detail), exc.details_payload)

    if isinstance(exc, ValidationError):
        return _response(status.HTTP_400_BAD_REQUEST, "VALIDATION_ERROR", "Invalid request.", exc.detail)

    if isinstance(exc, Throttled):
        return _response(status.HTTP_429_TOO_MANY_REQUESTS, "RATE_LIMIT_EXCEEDED", "API rate limit exceeded.", {"wait": exc.wait})

    if isinstance(exc, Http404):
        return _response(status.HTTP_404_NOT_FOUND, "NOT_FOUND", "Resource not found.")

    if isinstance(exc, DjangoPermissionDenied):
        return _response(status.HTTP_403_FORBIDDEN, "PERMISSION_DENIED", "You do not have permission to perform this action.")

    response = exception_handler(exc, context)
    if response is None:
        return _response(status.HTTP_500_INTERNAL_SERVER_ERROR, "INTERNAL_ERROR", "An unexpected error occurred.")

    code = getattr(exc, "default_code", None) or "API_ERROR"
    mapping = {
        "not_authenticated": ("UNAUTHENTICATED", status.HTTP_401_UNAUTHORIZED),
        "authentication_failed": ("UNAUTHENTICATED", status.HTTP_401_UNAUTHORIZED),
        "permission_denied": ("PERMISSION_DENIED", status.HTTP_403_FORBIDDEN),
        "not_found": ("NOT_FOUND", status.HTTP_404_NOT_FOUND),
        "throttled": ("RATE_LIMIT_EXCEEDED", status.HTTP_429_TOO_MANY_REQUESTS),
    }
    if code in mapping:
        mapped_code, mapped_status = mapping[code]
        message = "Authentication required." if mapped_code == "UNAUTHENTICATED" else str(getattr(exc, "detail", "Request failed."))
        if mapped_code == "PERMISSION_DENIED":
            message = "You do not have permission to perform this action."
        if mapped_code == "NOT_FOUND":
            message = "Resource not found."
        return _response(mapped_status, mapped_code, message, getattr(exc, "detail", {}))

    detail = response.data
    message = "Request failed."
    if isinstance(detail, dict) and "detail" in detail:
        message = str(detail["detail"])
        detail = {}
    elif isinstance(detail, list):
        message = str(detail[0]) if detail else message
    return _response(response.status_code, str(code).upper(), message, detail)


def _response(status_code: int, code: str, message: str, details: Any = None):
    from rest_framework.response import Response

    return Response(_error_payload(code, message, details), status=status_code)
