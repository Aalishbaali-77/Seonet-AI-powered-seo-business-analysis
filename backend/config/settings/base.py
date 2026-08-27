from __future__ import annotations

import base64
import hashlib
import os
from datetime import timedelta
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ROOT_DIR = BASE_DIR.parent

load_dotenv(ROOT_DIR / ".env")
load_dotenv(BASE_DIR / ".env")


def env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name, default)
    return value if value not in ("", None) else default


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


SECRET_KEY = env("DJANGO_SECRET_KEY", "insecure-dev-key-change-me")
DEBUG = env_bool("DJANGO_DEBUG", False)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

# Encrypts secrets (API keys, payment gateway credentials) at rest via
# apps.common.encryption.EncryptedJSONField. Set a real FIELD_ENCRYPTION_KEY
# in production; this derived fallback only keeps dev/test environments working
# without extra setup.
FIELD_ENCRYPTION_KEY = env("FIELD_ENCRYPTION_KEY") or base64.urlsafe_b64encode(
    hashlib.sha256(f"seonet-field-encryption:{SECRET_KEY}".encode()).digest()
).decode()

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "apps.common",
    "apps.core",
    "apps.users",
    "apps.tenants",
    "apps.rbac",
    "apps.auditlog",
    "apps.jobs",
    "apps.notifications",
    "apps.websites",
    "apps.crawler",
    "apps.audits",
    "apps.ai",
    "apps.leads",
    "apps.business",
    "apps.markets",
    "apps.opportunities",
    "apps.marketing",
    "apps.crm",
    "apps.integrations",
    "apps.usage",
    "apps.billing",
    "apps.platform",
    "apps.api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.users.middleware.JWTUserMiddleware",
    "apps.common.middleware.RequestIDMiddleware",
    "apps.tenants.middleware.TenantMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.common.middleware.SecurityHeadersMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

database_url = env("DATABASE_URL", f"sqlite:///{BASE_DIR / 'db.sqlite3'}")
DATABASES = {
    "default": dj_database_url.parse(
        database_url,
        conn_max_age=600,
        ssl_require=env_bool("DATABASE_SSL_REQUIRE", False),
    )
}

AUTH_USER_MODEL = "users.User"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = env("DJANGO_TIME_ZONE", "UTC") or "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

REDIS_URL = env("REDIS_URL", "redis://localhost:6379/0") or "redis://localhost:6379/0"
RABBITMQ_URL = env("RABBITMQ_URL", "amqp://guest:guest@localhost:5672//") or "amqp://guest:guest@localhost:5672//"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "seonet-local",
    }
}

CELERY_BROKER_URL = env("CELERY_BROKER_URL", RABBITMQ_URL) or RABBITMQ_URL
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", "redis://localhost:6379/1") or "redis://localhost:6379/1"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 60 * 30
CELERY_TASK_SOFT_TIME_LIMIT = 60 * 25
CELERY_TASK_DEFAULT_QUEUE = "default"
CELERY_TASK_QUEUES = {
    "default": {},
    "crawl": {},
    "audit": {},
    "ai": {},
    "leads": {},
    "crm": {},
    "reports": {},
    "notifications": {},
}

FEATURE_FLAGS = {
    "AI_AEO_ENABLED": env_bool("AI_AEO_ENABLED", False),
    "LEAD_DISCOVERY_ENABLED": env_bool("LEAD_DISCOVERY_ENABLED", True),
    "HUBSPOT_ENABLED": env_bool("HUBSPOT_ENABLED", False),
    "ODOO_ENABLED": env_bool("ODOO_ENABLED", False),
    "WHITE_LABEL_ENABLED": env_bool("WHITE_LABEL_ENABLED", False),
}

CRAWLER_MAX_PAGES = int(env("CRAWLER_MAX_PAGES", "20") or "20")
CRAWLER_MAX_DEPTH = int(env("CRAWLER_MAX_DEPTH", "3") or "3")
CRAWLER_TIMEOUT = int(env("CRAWLER_TIMEOUT", "10") or "10")
CRAWLER_MAX_RESPONSE_SIZE = int(env("CRAWLER_MAX_RESPONSE_SIZE", "2000000") or "2000000")
PERFORMANCE_THRESHOLDS = {}

CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000",
)
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
    "x-tenant-id",
    "x-request-id",
]
CORS_EXPOSE_HEADERS = ["Content-Disposition"]
CSRF_TRUSTED_ORIGINS = env_list(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000",
)

# Applied by apps.common.middleware.SecurityHeadersMiddleware. Most API responses
# are JSON, but this also covers the HTML surfaces: Django admin, Swagger docs
# (/api/docs/, served via jsdelivr CDN), and DRF's browsable API.
CONTENT_SECURITY_POLICY = {
    "default-src": ["'self'"],
    "base-uri": ["'self'"],
    "frame-ancestors": ["'none'"],
    "object-src": ["'none'"],
    "script-src": ["'self'", "https://cdn.jsdelivr.net"],
    "style-src": ["'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net"],
    "img-src": ["'self'", "data:", "https://cdn.jsdelivr.net"],
    "font-src": ["'self'", "data:", "https://cdn.jsdelivr.net"],
    "connect-src": ["'self'"],
}

AUTH_COOKIE_ACCESS = "seonet_access"
AUTH_COOKIE_REFRESH = "seonet_refresh"
AUTH_COOKIE_DOMAIN = env("AUTH_COOKIE_DOMAIN") or None
AUTH_COOKIE_SECURE = env_bool("AUTH_COOKIE_SECURE", False)
AUTH_COOKIE_SAMESITE = env("AUTH_COOKIE_SAMESITE", "Lax") or "Lax"
AUTH_COOKIE_HTTPONLY = True
AUTH_COOKIE_PATH = "/"

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.users.authentication.TenantApiTokenAuthentication",
        "apps.users.authentication.CookieJWTAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "apps.common.pagination.StandardPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "30/minute",
        "user": "120/minute",
        "auth": "10/minute",
    },
    "EXCEPTION_HANDLER": "apps.common.exceptions.api_exception_handler",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Seonet API",
    "DESCRIPTION": "Seonet — AI-Powered Business Growth Intelligence Platform",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SERVE_PERMISSIONS": ["rest_framework.permissions.AllowAny"],
}

EMAIL_BACKEND = env("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "Seonet <noreply@localhost>")

APP_VERSION = env("APP_VERSION", "0.1.0") or "0.1.0"
SENTRY_DSN = env("SENTRY_DSN")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "apps.common.logging.JSONFormatter",
        }
    },
    "filters": {
        "request_context": {
            "()": "apps.common.logging.RequestContextFilter",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "filters": ["request_context"],
        }
    },
    "root": {
        "handlers": ["console"],
        "level": env("LOG_LEVEL", "INFO") or "INFO",
    },
}

if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        environment=env("SENTRY_ENVIRONMENT", "development"),
        traces_sample_rate=0.1,
        send_default_pii=False,
    )
