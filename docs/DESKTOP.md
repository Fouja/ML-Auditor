# ML-Auditor Desktop App

This document explains the full desktop build for Ubuntu: a single installable
`.deb` package that bundles the Next.js frontend, the Django backend, and a
local SQLite database.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         ML-Auditor Desktop                          │
│  ┌─────────────────┐      Tauri commands (Rust)      ┌───────────┐ │
│  │  Next.js UI     │  ◄─────────────────────────────►  │  Rust     │ │
│  │  (static export)│                                 │  shell    │ │
│  └─────────────────┘                                 └─────┬─────┘ │
│                                                            │        │
│                                                            ▼        │
│                                                   ┌──────────────┐  │
│                                                   │ Django       │  │
│                                                   │ sidecar      │  │
│                                                   │ (PyInstaller)│  │
│                                                   └──────┬───────┘  │
│                                                          │          │
│                                                          ▼          │
│                                                   ┌──────────────┐  │
│                                                   │ SQLite file  │  │
│                                                   │ + sqlite-vec │  │
│                                                   └──────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### Single-file Rust entry point

All desktop logic lives in one file:

```
frontend/src-tauri/src/main.rs
```

Responsibilities:

1. **Start the backend sidecar** on a free TCP port.
2. **Wait for `/api/health/`** to return `200`.
3. **Show the main window** only after the backend is healthy.
4. **Expose four Tauri commands** to the frontend:
   - `get_backend_url()` — dynamic backend base URL
   - `is_desktop_mode()` — `true` inside the desktop wrapper
   - `reset_local_database()` — wipe SQLite and re-run migrations
   - `check_for_app_update()` — query GitHub releases
5. **Kill the backend** when the app exits.
6. **System tray** — close button hides to tray; quit from tray menu exits.

---

## Backend: Desktop Mode

When the Tauri sidecar launches the Python executable it sets:

```
DJANGO_SETTINGS_MODULE=config.desktop_settings
ML_AUDITOR_DATA_DIR=<per-user app data dir>
DESKTOP_DB_PATH=<SQLite file>
DESKTOP_LOG_PATH=<backend.log>
```

`backend/config/desktop_settings.py` is the dedicated desktop settings module:

- SQLite database (no PostgreSQL server).
- Redis/Celery/Channels disabled; tasks run in-process (`CELERY_TASK_ALWAYS_EAGER`).
- Elastic APM/Sentry disabled.
- JobChameleon integration disabled.
- sqlite-vec extension loaded on every SQLite connection for native vector search.
- If sqlite-vec is unavailable, the retriever falls back to Python cosine similarity.

### Vector search on SQLite

- Field: `apps/document_chunks/fields.py` stores JSON text on SQLite and real
  `pgvector` columns on Postgres.
- Retriever: `apps/document_chunks/services/rag/retriever.py` picks
  `pgvector` on Postgres, `sqlite-vec` on SQLite, then Python cosine as final
  fallback.
- sqlite-vec integration: `apps/document_chunks/services/rag/sqlite_vec.py`
  creates a virtual table and syncs embeddings lazily.

---

## Sidecar Build

The backend is frozen into one executable with PyInstaller:

```bash
cd backend
DJANGO_SETTINGS_MODULE=config.desktop_settings ../.venv/bin/pyinstaller pyinstaller_desktop.spec --clean --noconfirm
```

Output:

```
backend/dist/ml-auditor-backend
```

It is copied to:

```
frontend/src-tauri/binaries/ml-auditor-backend
frontend/src-tauri/binaries/ml-auditor-backend-x86_64-unknown-linux-gnu
```

(Tauri needs the target-triple suffix for bundling.)

---

## Frontend Desktop Integration

Single TypeScript module:

```
frontend/src/lib/desktop.ts
```

It wraps `@tauri-apps/api/core` `invoke()` and exposes:

- `isDesktopMode()`
- `getBackendUrl()`
- `resetLocalDatabase()`
- `checkForAppUpdate()`

`frontend/src/lib/api.ts` uses `getBackendUrl()` so every Axios request goes to
the Tauri-managed local backend instead of the hard-coded web URL.

### Desktop settings page

```
frontend/src/app/desktop/page.tsx
```

- Shows the local backend URL.
- **Delete Local Database** button — calls `reset_local_database`.
- **Check for Updates** button — calls GitHub releases via Tauri updater.

### Sidebar entry

`frontend/src/components/layout/sidebar.tsx` adds a **Desktop App** menu item.

### JobChameleon hidden on desktop

`frontend/src/components/dashboard/integrations-panel.tsx` does not render the
JobChameleon card when `isDesktopMode()` is true because the desktop build has
no Docker microservice.

---

## Build the `.deb`

Prerequisites on Ubuntu:

```bash
sudo apt update
sudo apt install libwebkit2gtk-4.1-dev libgtk-3-dev libayatana-appindicator3-dev
```

Build:

```bash
cd frontend
TAURI_SIGNING_PRIVATE_KEY_PATH=src-tauri/ml-auditor-updater.key \
  TAURI_BUILD=1 \
  npm run tauri:build
```

Output:

```
frontend/src-tauri/target/release/bundle/deb/ML-Auditor_0.6.9_amd64.deb
```

The `.desktop` file is registered automatically, so the app appears in the
application grid and can be launched with a double-click after installing.

Install:

```bash
sudo dpkg -i frontend/src-tauri/target/release/bundle/deb/ML-Auditor_0.6.9_amd64.deb
```

Run:

```bash
ml-auditor-desktop
```

Or launch from the GNOME/KDE application menu.

---

## Auto-Updater

Tauri updater is configured in:

```
frontend/src-tauri/tauri.conf.json
```

Endpoint:

```
https://github.com/Fouja/ML-Auditor/releases/latest/download/latest.json
```

To publish an update:

1. Bump `version` in `frontend/package.json`, `frontend/package-lock.json`,
   `frontend/src-tauri/tauri.conf.json`, and `frontend/src-tauri/Cargo.toml`.
2. Commit the version bump and push a tag like `v0.6.9`.
3. The GitHub Actions workflow (`.github/workflows/release.yml`) builds the
   sidecar, builds the `.deb`, signs it, generates `latest.json`, and creates
   the GitHub release automatically.

Required GitHub secret:

- `TAURI_SIGNING_PRIVATE_KEY` — paste the full contents of
  `frontend/src-tauri/ml-auditor-updater.key`.

The workflow uploads:

- `ML-Auditor_<version>_amd64.deb`
- `ML-Auditor_<version>_amd64.deb.sig`
- `latest.json`

The signing private key file is gitignored; keep it secret. The public key is
committed in `tauri.conf.json`.

---

## Files Added/Modified

### New files

- `frontend/src-tauri/` — Tauri app shell (Cargo, config, Rust source, icons, updater key)
- `backend/config/desktop_settings.py` — SQLite desktop settings
- `backend/apps/document_chunks/services/rag/sqlite_vec.py` — sqlite-vec search
- `backend/apps/users/management/commands/reset_desktop_db.py` — DB reset command
- `backend/pyinstaller_desktop.spec` — PyInstaller sidecar build
- `frontend/src/lib/desktop.ts` — frontend Tauri API wrapper
- `frontend/src/app/desktop/page.tsx` — desktop settings UI
- `docs/DESKTOP.md` — this document

### Modified files

- `frontend/src/app/layout.tsx` — replaced raw `<script>` with `next/script`
- `frontend/next.config.js` — static export for Tauri
- `frontend/package.json` — Tauri scripts and dependencies
- `frontend/src/lib/api.ts` — dynamic backend URL
- `frontend/src/components/layout/sidebar.tsx` — Desktop App link
- `frontend/src/components/dashboard/integrations-panel.tsx` — hide JobChameleon
- `backend/config/urls.py` — added `/api/health/`
- `backend/apps/document_chunks/services/rag/retriever.py` — sqlite-vec path
