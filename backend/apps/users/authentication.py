from __future__ import annotations

from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken


class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        header = self.get_header(request)
        if header is not None:
            return super().authenticate(request)
        raw_token = request.COOKIES.get(settings.AUTH_COOKIE_ACCESS)
        if not raw_token:
            return None
        try:
            validated_token = self.get_validated_token(raw_token.encode())
            return self.get_user(validated_token), validated_token
        except (InvalidToken, AuthenticationFailed):
            return None


class TenantApiTokenAuthentication(BaseAuthentication):
    def authenticate(self, request):
        from apps.integrations.tokens import TOKEN_PREFIX, authenticate_api_token

        header = request.headers.get("Authorization") or ""
        if not header.lower().startswith("bearer "):
            return None
        raw = header.split(" ", 1)[1].strip()
        if not raw.startswith(TOKEN_PREFIX):
            return None
        token = authenticate_api_token(raw)
        if token is None:
            raise AuthenticationFailed("Invalid API token.")
        request.api_token_tenant = token.tenant
        return token.created_by, token
