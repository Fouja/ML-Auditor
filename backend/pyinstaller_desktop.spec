# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for the ML-Auditor desktop backend sidecar.

Builds a single executable ``ml-auditor-backend`` that bundles Django and all
backend apps so Tauri can ship it next to the desktop app binary.

Usage:
    cd backend
    DJANGO_SETTINGS_MODULE=config.desktop_settings ../.venv/bin/pyinstaller pyinstaller_desktop.spec --clean --noconfirm
    cp dist/ml-auditor-backend ../frontend/src-tauri/binaries/
"""

import os
from pathlib import Path

from PyInstaller.building.api import PYZ, EXE
from PyInstaller.building.build_main import Analysis
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

# Make Django happy during PyInstaller's import analysis.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.desktop_settings")

# Base paths
ROOT = Path(SPECPATH).resolve()  # backend/
PROJECT_ROOT = ROOT.parent
VENV = PROJECT_ROOT / ".venv"

block_cipher = None

# ---------------------------------------------------------------------------
# Collect data files (templates, migrations, locale, static, etc.)
# ---------------------------------------------------------------------------

def safe_collect_data(package: str):
    try:
        return collect_data_files(package, include_py_files=True)
    except Exception:
        return []


def safe_collect_submodules(package: str):
    try:
        return collect_submodules(package, on_error="ignore")
    except Exception:
        return []


packages_to_collect = [
    "django",
    "ninja",
    "ninja_extra",
    "ninja_jwt",
    "rest_framework",
    "corsheaders",
    "celery",
    "django_celery_beat",
    "django_celery_results",
    "rest_framework_simplejwt",
    "django_rest_passwordreset",
    "django_redis",
    "channels",
    "channels_redis",
    "psycopg",
    "psycopg_binary",
    "pgvector",
    "sqlite_vec",
    "openai",
    "langchain_core",
    "langchain_openai",
    "langchain_anthropic",
    "langgraph",
    "reportlab",
    "docx",
    "pptx",
    "google_auth",
    "googleapiclient",
    "sentry_sdk",
    "structlog",
    "elasticapm",
    "cryptography",
    "pydantic",
    "httpx",
    "bs4",
    "feedparser",
    "mcp",
    "graphifyy",
]

all_datas = []
all_hiddenimports = []
for pkg in packages_to_collect:
    all_datas.extend(safe_collect_data(pkg))
    all_hiddenimports.extend(safe_collect_submodules(pkg))

# ---------------------------------------------------------------------------
# Local apps
# ---------------------------------------------------------------------------

local_apps = [
    "apps.users",
    "apps.alerts",
    "apps.agents",
    "apps.workspace",
    "apps.integrations",
    "apps.data_streams",
    "apps.document_chunks",
    "apps.logs",
]

for app in local_apps:
    all_hiddenimports.extend([
        app,
        f"{app}.models",
        f"{app}.admin",
        f"{app}.api",
        f"{app}.services",
        f"{app}.signals",
        f"{app}.migrations",
    ])
    # Include migrations as data files.
    migrations_dir = ROOT / app.replace(".", "/") / "migrations"
    if migrations_dir.exists():
        all_datas.append((str(migrations_dir), f"{app.replace('.', '/')}/migrations"))

# Config package (settings, urls, wsgi, api, celery)
all_hiddenimports += [
    "config",
    "config.desktop_settings",
    "config.settings",
    "config.celery",
    "config.urls",
    "config.wsgi",
    "config.api",
    "config.security",
]
all_datas.append((str(ROOT / "config"), "config"))

# Management commands used by the desktop app.
all_hiddenimports += [
    "apps.users.management.commands.reset_desktop_db",
]

# Common runtime modules that PyInstaller sometimes misses.
all_hiddenimports += [
    "pkg_resources",
    "pkg_resources.py2_warn",
    "setuptools",
    "xml.etree.ElementTree",
    "django.contrib.postgres",
    "django.contrib.postgres.operations",
    "django.contrib.postgres.signals",
    "django.contrib.postgres.forms",
    "django.contrib.postgres.fields",
    "django.db.backends.sqlite3",
]

a = Analysis(
    [str(ROOT / "manage.py")],
    pathex=[str(ROOT), str(VENV / "lib" / "python3.14" / "site-packages")],
    binaries=[],
    datas=all_datas,
    hiddenimports=all_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="ml-auditor-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
