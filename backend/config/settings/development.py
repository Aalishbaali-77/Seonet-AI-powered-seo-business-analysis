import socket
from urllib.parse import urlparse

from django.conf import global_settings
from django.contrib.auth.hashers import PBKDF2PasswordHasher

from .base import *  # noqa: F403

DEBUG = env_bool("DJANGO_DEBUG", True)  # noqa: F405

STORAGES["staticfiles"]["BACKEND"] = "django.contrib.staticfiles.storage.StaticFilesStorage"  # noqa: F405


def _redis_reachable(url: str, timeout: float = 0.2) -> bool:
    parsed = urlparse(url)
    try:
        with socket.create_connection((parsed.hostname, parsed.port or 6379), timeout=timeout):
            return True
    except OSError:
        return False


if REDIS_URL and REDIS_URL.startswith("redis://") and _redis_reachable(REDIS_URL):  # noqa: F405
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,  # noqa: F405
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "IGNORE_EXCEPTIONS": True,
                "SOCKET_CONNECT_TIMEOUT": 1,
                "SOCKET_TIMEOUT": 1,
            },
        }
    }
else:
    # Redis isn't reachable (or isn't configured) — fall back to an in-process
    # cache so every request doesn't block waiting on a dead connection.
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "sipulse-dev",
        }
    }

CELERY_TASK_ALWAYS_EAGER = env_bool("CELERY_TASK_ALWAYS_EAGER", True)  # noqa: F405


class FastDevPBKDF2Hasher(PBKDF2PasswordHasher):
    """Same algorithm as production, far fewer iterations so local logins are instant."""

    iterations = 20_000


PASSWORD_HASHERS = [
    "config.settings.development.FastDevPBKDF2Hasher",
    *global_settings.PASSWORD_HASHERS,
]
