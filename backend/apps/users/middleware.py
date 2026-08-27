from __future__ import annotations

from apps.users.authentication import CookieJWTAuthentication


class JWTUserMiddleware:
    """Populate request.user from JWT cookies/headers before tenant resolution."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.authenticator = CookieJWTAuthentication()

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            try:
                result = self.authenticator.authenticate(request)
            except Exception:
                result = None
            if result is not None:
                request.user, request.auth = result
        return self.get_response(request)
