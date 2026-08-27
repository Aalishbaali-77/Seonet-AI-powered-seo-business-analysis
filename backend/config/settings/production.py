from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403

DEBUG = False

if not env("FIELD_ENCRYPTION_KEY"):  # noqa: F405
    raise ImproperlyConfigured(
        "FIELD_ENCRYPTION_KEY must be set in production so stored secrets aren't "
        "encrypted with a key derived from DJANGO_SECRET_KEY."
    )
AUTH_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)  # noqa: F405
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,  # noqa: F405
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    }
}
