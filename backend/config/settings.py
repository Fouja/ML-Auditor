"""
Django settings for ML-Auditor project.
Modular monolithic architecture with environment-based configuration.
"""

import json
import logging
import os
from datetime import timedelta
from pathlib import Path

import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Environment variables
env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    DJANGO_SECRET_KEY=(str, "django-insecure-change-me-in-production"),
    DJANGO_DATABASE_URL=(
        str,
        "postgres://mlauditor:mlauditor@localhost:5432/mlauditor_db",
    ),
    DJANGO_CACHE_URL=(str, "redis://localhost:6379/0"),
    DJANGO_CELERY_BROKER_URL=(str, "redis://localhost:6379/1"),
    DJANGO_CELERY_RESULT_BACKEND=(str, "redis://localhost:6379/2"),
    DJANGO_CHANNELS_LAYERS=(str, "redis://localhost:6379/3"),
    JWT_SECRET_KEY=(str, "jwt-secret-change-me-in-production"),
    JWT_ACCESS_TOKEN_LIFETIME=(int, 3600),
    JWT_REFRESH_TOKEN_LIFETIME=(int, 604800),
    NIM_API_KEY=(str, ""),
    NIM_BASE_URL=(str, "https://integrate.api.nvidia.com/v1"),
    NIM_MODEL=(str, "meta/llama-3.1-8b-instruct"),
    JC_URL=(str, "http://localhost:8787"),
    JC_MCP_URL=(str, "http://localhost:8788/mcp"),
    JC_PUBLIC_URL=(str, "http://localhost:8787"),
    JCAPP_PUBLIC_URL=(str, "http://localhost:8088"),
    JC_API_TOKEN=(str, ""),
    PLAID_CLIENT_ID=(str, ""),
    PLAID_SECRET=(str, ""),
    PLAID_ENV=(str, "sandbox"),
    GOOGLE_OAUTH_CLIENT_ID=(str, ""),
    GOOGLE_OAUTH_CLIENT_SECRET=(str, ""),
    CANVA_CLIENT_ID=(str, ""),
    CANVA_CLIENT_SECRET=(str, ""),
    SENTRY_DSN=(str, ""),
    ELASTICSEARCH_URL=(str, "http://localhost:9200"),
)

# Take environment variables from .env file
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("DJANGO_SECRET_KEY")

# Optional override used to derive the at-rest encryption key for stored
# credentials (e.g. LLMConfiguration.api_key). When unset, the key is derived
# from DJANGO_SECRET_KEY.
SECRET_ENCRYPTION_KEY = env("SECRET_ENCRYPTION_KEY", default="")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env("DJANGO_DEBUG")

ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")

# Refuse to run with known-insecure secrets outside of DEBUG.
_INSECURE_SECRETS = {
    "django-insecure-change-me-in-production",
    "django-insecure-dev-key-change-in-production",
    "jwt-secret-change-me-in-production",
}

if not DEBUG:
    from django.core.exceptions import ImproperlyConfigured

    if SECRET_KEY in _INSECURE_SECRETS:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY is set to an insecure default. Generate a strong "
            "random key (scripts/generate_secrets.sh) and put it in .env."
        )
    if env("JWT_SECRET_KEY") in _INSECURE_SECRETS:
        raise ImproperlyConfigured(
            "JWT_SECRET_KEY is set to an insecure default. Generate a strong "
            "random key (scripts/generate_secrets.sh) and put it in .env."
        )

# Application definition

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "ninja",
    "ninja_extra",
    "ninja_jwt",
    "corsheaders",
    "django_celery_beat",
    "django_celery_results",
    "elasticapm.contrib.django",
]

LOCAL_APPS = [
    "apps.users",
    "apps.alerts",
    "apps.agents",
    "apps.workspace",
    "apps.integrations",
    "apps.data_streams",
    "apps.document_chunks",
    "apps.logs",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "elasticapm.contrib.django.middleware.TracingMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.users.middleware.JWTAuthenticationMiddleware",
    "apps.users.middleware.RequestLoggingMiddleware",
    "apps.users.middleware.ErrorHandlingMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database
DATABASES = {
    "default": env.db("DJANGO_DATABASE_URL"),
}

# Cache
CACHES = {
    "default": env.cache("DJANGO_CACHE_URL"),
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Media files
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Custom User Model
AUTH_USER_MODEL = "users.User"

# CORS
CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
]

# CSRF
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
]

CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SAMESITE = "Lax"

# Celery Configuration
CELERY_BROKER_URL = env("DJANGO_CELERY_BROKER_URL")
CELERY_RESULT_BACKEND = env("DJANGO_CELERY_RESULT_BACKEND")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

ELASTICSEARCH_URL = env("ELASTICSEARCH_URL")
WEB_TOOLS_URL = env("WEB_TOOLS_URL", default="http://localhost:8090")

# Elastic APM — traces from the Django app are sent to the apm-server service
# (docker-compose) and visualised in Kibana → Observability → APM.
ELASTIC_APM = {
    "SERVICE_NAME": env("ELASTIC_APM_SERVICE_NAME", default="ml-auditor-backend"),
    "SERVER_URL": env("ELASTIC_APM_SERVER_URL", default="http://apm-server:8200"),
    "ENVIRONMENT": env("DJANGO_ENV", default="development"),
    "ENABLED": env.bool("ELASTIC_APM_ENABLED", default=True),
    "DEBUG": DEBUG,
}

# Channels
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [env("DJANGO_CHANNELS_LAYERS")],
        },
    },
}

# JWT Configuration (single source of truth shared by NINJA_JWT and SIMPLE_JWT)
_JWT_ACCESS_TOKEN_LIFETIME = timedelta(seconds=env("JWT_ACCESS_TOKEN_LIFETIME"))
_JWT_REFRESH_TOKEN_LIFETIME = timedelta(seconds=env("JWT_REFRESH_TOKEN_LIFETIME"))
_JWT_SIGNING_KEY = env("JWT_SECRET_KEY")

NINJA_JWT = {
    "ACCESS_TOKEN_LIFETIME": _JWT_ACCESS_TOKEN_LIFETIME,
    "REFRESH_TOKEN_LIFETIME": _JWT_REFRESH_TOKEN_LIFETIME,
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "SIGNING_KEY": _JWT_SIGNING_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# SimpleJWT — used by the custom login/refresh views via RefreshToken.for_user.
SIMPLE_JWT = dict(NINJA_JWT)

# NIM (NVIDIA Inference Microservices)
NIM_API_KEY = env("NIM_API_KEY")
NIM_BASE_URL = env("NIM_BASE_URL")
NIM_MODEL = env("NIM_MODEL")

# JobChameleon microservice (job intelligence)
JC_URL = env("JC_URL", default="http://localhost:8787")
JC_MCP_URL = env("JC_MCP_URL", default="http://localhost:8788/mcp")
# Browser-facing URLs (the user's browser opens these, NOT the docker-internal
# service names) — used by the JOBchameleon launch flow.
JC_PUBLIC_URL = env("JC_PUBLIC_URL", default="http://localhost:8787")
JCAPP_PUBLIC_URL = env("JCAPP_PUBLIC_URL", default="http://localhost:8088")
JC_API_TOKEN = env("JC_API_TOKEN", default="")

# Plaid / Google OAuth / Canva
PLAID_CLIENT_ID = env("PLAID_CLIENT_ID", default="")
PLAID_SECRET = env("PLAID_SECRET", default="")
PLAID_ENV = env("PLAID_ENV", default="sandbox")
GOOGLE_OAUTH_CLIENT_ID = env("GOOGLE_OAUTH_CLIENT_ID", default="")
GOOGLE_OAUTH_CLIENT_SECRET = env("GOOGLE_OAUTH_CLIENT_SECRET", default="")
GOOGLE_OAUTH_REDIRECT_URI = env(
    "GOOGLE_OAUTH_REDIRECT_URI",
    default="http://localhost:8000/api/integrations/oauth/google/callback",
)
CANVA_CLIENT_ID = env("CANVA_CLIENT_ID", default="")
CANVA_CLIENT_SECRET = env("CANVA_CLIENT_SECRET", default="")
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:3000")

# Sentry Configuration
SENTRY_DSN = env("SENTRY_DSN")
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=True,
    )


# ===========================================
# Structured Logging for ELK Stack
# ===========================================


class JSONFormatter(logging.Formatter):
    """JSON log formatter for Elasticsearch ingestion."""

    def format(self, record):
        log_entry = {
            "@timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": "backend",
            "stack": "django",
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if hasattr(record, "request_method"):
            log_entry["request_method"] = record.request_method
        if hasattr(record, "request_path"):
            log_entry["request_path"] = record.request_path
        if hasattr(record, "status_code"):
            log_entry["status_code"] = record.status_code
        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id
        if hasattr(record, "ip_address"):
            log_entry["ip_address"] = record.ip_address
        if hasattr(record, "response_time"):
            log_entry["response_time"] = record.response_time

        if hasattr(record, "metrics") and isinstance(record.metrics, dict):
            for k, v in record.metrics.items():
                log_entry[k] = v

        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info),
            }

        return json.dumps(log_entry, default=str)


LOG_DIR = Path(os.environ.get("LOG_DIR", BASE_DIR.parent / "logs" / "backend"))
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} {message}",
            "style": "{",
        },
        "json": {
            "()": JSONFormatter,
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "json_console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": LOG_DIR / "django.log",
            "formatter": "json",
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "apps": {
            "handlers": ["json_console", "file"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
