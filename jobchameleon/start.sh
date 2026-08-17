#!/bin/sh
set -e
cd /app

PY=/app/.venv/bin/python

# Seed JobChameleon's LLM settings to use the same NVIDIA NIM key/model as ML-Auditor.
$PY - <<'PY'
import os
from data.sqlite.settings import save_settings

payload = {
    "llm_provider": "nvidia",
    "nvidia_api_key": os.environ.get("NVIDIA_API_KEY", ""),
    "nvidia_model": os.environ.get("NVIDIA_MODEL", ""),
}
save_settings({k: v for k, v in payload.items() if v})
print("JobChameleon LLM settings:", {k: bool(v) for k, v in payload.items()})
PY

$PY mcp_http.py &
MCP_PID=$!

cleanup() {
    kill "$MCP_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

exec $PY main.py --port 8787
