"""
Django settings for the ML-Auditor **desktop** build.

This module is used when the backend is launched as a Tauri sidecar. It replaces
PostgreSQL/Redis/Celery with local SQLite and in-process fallbacks so the app
runs without any external services.

Key differences from ``config.settings``:
* SQLite file database (vector search via sqlite-vec + JSON-embedding fallback)
* Redis/Celery/Channels/Elastic APM are disabled
* JobChameleon microservice integration is disabled
* Static/media roots point inside the Tauri app data directory
* Logging writes to a single backend.log file next to the SQLite database
"""

import os
from pathlib import Path

# Desktop builds always run in debug-ish mode (single user, local SQLite).
# Setting this before importing the base settings prevents the base settings
# from raising ImproperlyConfigured for the default secret key.
os.environ["DJANGO_DEBUG"] = "True"

# Pull in the base settings, then override the parts that don't fit a desktop app.
from config.settings import *  # noqa: F401,F403


def _load_sqlite_vec(sender, connection, **kwargs):
    """Load the sqlite-vec extension on every SQLite connection.

    This gives the desktop build native vector distance functions even though
    the database is SQLite instead of Postgres+pgvector.
    """
    if connection.vendor != "sqlite":
        return
    try:
        import sqlite_vec  # noqa: F401

        connection.connection.enable_load_extension(True)
        sqlite_vec.load(connection.connection)
        connection.connection.enable_load_extension(False)
    except Exception:
        # sqlite-vec is optional; the retriever will fall back to Python cosine.
        pass


from django.db.backends.signals import connection_created  # noqa: E402

connection_created.connect(_load_sqlite_vec)

# -----------------------------------------------------------------------------
# Paths
# -----------------------------------------------------------------------------

# Tauri passes the per-user data directory through this environment variable.
DATA_DIR = Path(os.environ.get("ML_AUDITOR_DATA_DIR", BASE_DIR.parent / "desktop-data"))  # noqa: F405
DATA_DIR.mkdir(parents=True, exist_ok=True)

DESKTOP_DB_PATH = Path(os.environ.get("DESKTOP_DB_PATH", DATA_DIR / "ml-auditor.sqlite3"))
DESKTOP_LOG_PATH = Path(os.environ.get("DESKTOP_LOG_PATH", DATA_DIR / "backend.log"))

# -----------------------------------------------------------------------------
# Security / runtime
# -----------------------------------------------------------------------------

DEBUG = os.environ.get("DESKTOP_DEBUG", "false").lower() == "true"
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "desktop-insecure-key-replaced-by-tauri-on-first-launch",
)

# The frontend served by Tauri talks to the local backend.
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]
CORS_ALLOW_ALL_ORIGINS = True
CSRF_TRUSTED_ORIGINS = ["http://localhost", "http://127.0.0.1", "tauri://localhost"]

# -----------------------------------------------------------------------------
# Database — SQLite for single-file desktop storage
# -----------------------------------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(DESKTOP_DB_PATH),
    }
}

# -----------------------------------------------------------------------------
# Cache / sessions / channels — disable Redis, use local memory / file
# -----------------------------------------------------------------------------

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}

# Celery is not used in desktop mode; tasks run synchronously.
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache"
CELERY_CACHE_BACKEND = "default"
CELERY_TASK_ALWAYS_EAGER = True  # Run tasks in-process immediately

# -----------------------------------------------------------------------------
# Static / media files
# -----------------------------------------------------------------------------

STATIC_ROOT = DATA_DIR / "staticfiles"
MEDIA_ROOT = DATA_DIR / "media"

# -----------------------------------------------------------------------------
# Monitoring — disable external APM/ELK/Sentry in desktop builds
# -----------------------------------------------------------------------------

ELASTIC_APM = {
    **ELASTIC_APM,  # noqa: F405
    "ENABLED": False,
}

# -----------------------------------------------------------------------------
# Integrations — disable JobChameleon microservice for desktop
# -----------------------------------------------------------------------------

JC_URL = ""
JC_MCP_URL = ""
JC_PUBLIC_URL = ""
JCAPP_PUBLIC_URL = ""
JC_API_TOKEN = ""

# -----------------------------------------------------------------------------
# Logging — single file next to the SQLite database
# -----------------------------------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": str(DESKTOP_LOG_PATH),
            "formatter": "verbose",
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
            "handlers": ["console", "file"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
