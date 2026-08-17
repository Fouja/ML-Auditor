#!/bin/sh
set -e

python -m mcp_app &
MCP_PID=$!

cleanup() {
    kill "$MCP_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

uvicorn main:app --host 0.0.0.0 --port 8090
