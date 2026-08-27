from __future__ import annotations

from django.conf import settings
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken


def _cookie_kwargs(*, max_age: int) -> dict:
    return {
        "httponly": settings.AUTH_COOKIE_HTTPONLY,
        "secure": settings.AUTH_COOKIE_SECURE,
        "samesite": settings.AUTH_COOKIE_SAMESITE,
        "path": settings.AUTH_COOKIE_PATH,
        "domain": settings.AUTH_COOKIE_DOMAIN,
        "max_age": max_age,
    }


def set_auth_cookies(response: Response, refresh: RefreshToken) -> Response:
    access_max_age = int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds())
    refresh_max_age = int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds())
    response.set_cookie(settings.AUTH_COOKIE_ACCESS, str(refresh.access_token), **_cookie_kwargs(max_age=access_max_age))
    response.set_cookie(settings.AUTH_COOKIE_REFRESH, str(refresh), **_cookie_kwargs(max_age=refresh_max_age))
    return response


def clear_auth_cookies(response: Response) -> Response:
    response.delete_cookie(settings.AUTH_COOKIE_ACCESS, path=settings.AUTH_COOKIE_PATH, domain=settings.AUTH_COOKIE_DOMAIN)
    response.delete_cookie(settings.AUTH_COOKIE_REFRESH, path=settings.AUTH_COOKIE_PATH, domain=settings.AUTH_COOKIE_DOMAIN)
    return response


def tokens_for_user(user) -> RefreshToken:
    return RefreshToken.for_user(user)
