from __future__ import annotations

from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

from apps.common.request_context import new_request_id, set_request_id, set_tenant_id


class RequestIDMiddleware(MiddlewareMixin):
    header = "HTTP_X_REQUEST_ID"

    def process_request(self, request):
        request_id = request.META.get(self.header) or new_request_id()
        request.request_id = request_id
        set_request_id(request_id)
        set_tenant_id("")

    def process_response(self, request, response):
        request_id = getattr(request, "request_id", None) or new_request_id()
        response["X-Request-ID"] = request_id
        return response


def _content_security_policy() -> str:
    policy = getattr(settings, "CONTENT_SECURITY_POLICY", {})
    return "; ".join(f"{directive} {' '.join(sources)}" for directive, sources in policy.items())


class SecurityHeadersMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        response.setdefault("X-Content-Type-Options", "nosniff")
        response.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.setdefault("X-Frame-Options", "DENY")
        if not settings.DEBUG:
            response.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        csp = _content_security_policy()
        if csp:
            response.setdefault("Content-Security-Policy", csp)
        return response
