"""Manage the JobCamelonapp Docker container from the Django backend.

The "Run JobCamelonapp container" button on the JobChameleon integration card
calls ``POST /api/agents/jobcamelonapp/start``. This module talks to the host
Docker daemon over the unix socket (mounted into the backend container at
``/var/run/docker.sock``) using only the Python stdlib, and creates/starts a
fresh ``mlauditor_jobcamelonapp`` container on the ML-Auditor compose network.

The image (``mlauditor/jobcamelonapp:latest``) must exist once:
    docker build -t mlauditor/jobcamelonapp:latest ./JobCamelonapp
"""

from __future__ import annotations

import http.client
import json
import logging
import os
import socket
from typing import Any, Optional

from django.conf import settings

logger = logging.getLogger(__name__)

CONTAINER_NAME = "mlauditor_jobcamelonapp"
IMAGE = "mlauditor/jobcamelonapp:latest"
UNIX_SOCKET = os.environ.get("DOCKER_SOCK", "/var/run/docker.sock")
# The container's nginx web UI listens on 8088 internally (fixed by the image's
# nginx.conf). The host-side binding is decoupled via JCAPP_WEB_HOST_PORT so the
# container can run even when something else on the host already occupies 8088
# (e.g. the Wekan snap's FerretDB), without editing the image.
WEB_PORT = int(os.environ.get("JCAPP_WEB_PORT", "8088"))
WEB_HOST_PORT = int(os.environ.get("JCAPP_WEB_HOST_PORT", str(WEB_PORT)))
GATEWAY_PORT = int(os.environ.get("JCAPP_GATEWAY_PORT", "1403"))
MCP_PORT = int(os.environ.get("JCAPP_MCP_PORT", "8790"))
DEFAULT_NETWORK = os.environ.get("JCAPP_DOCKER_NETWORK", "ml-auditor_default")


class _UnixHTTPConnection(http.client.HTTPConnection):
    def __init__(self, socket_path: str):
        super().__init__("docker")
        self._socket_path = socket_path

    def connect(self) -> None:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(30)
        sock.connect(self._socket_path)
        self.sock = sock


def _docker_request(method: str, path: str, body: Optional[dict] = None) -> tuple[int, Any]:
    conn = _UnixHTTPConnection(UNIX_SOCKET)
    headers = {"Content-Type": "application/json"} if body is not None else {}
    payload = json.dumps(body) if body is not None else None
    try:
        conn.request(method, path, body=payload, headers=headers)
        resp = conn.getresponse()
        data = resp.read()
        try:
            parsed = json.loads(data) if data else None
        except json.JSONDecodeError:
            parsed = data.decode("utf-8", "replace")
        return resp.status, parsed
    finally:
        conn.close()


def _public_url() -> str:
    return getattr(settings, "JCAPP_PUBLIC_URL", "http://localhost:8088")


def _detect_network() -> str:
    """Join the same docker network as the jobchameleon microservice."""
    status, info = _docker_request("GET", "/containers/mlauditor_jobchameleon/json")
    if status == 200:
        networks = info.get("NetworkSettings", {}).get("Networks", {}) or {}
        if networks:
            return next(iter(networks))
    return DEFAULT_NETWORK


def _container_env() -> list[str]:
    env = {
        "JC_HOST": "0.0.0.0",
        "JC_TOKEN": getattr(settings, "JC_API_TOKEN", ""),
        "JC_ALLOWED_HOSTS": "jobcamelonapp,localhost,127.0.0.1",
        "JC_MCP_URL": "http://jobchameleon:8788/mcp",
        "JC_MCP_PORT": str(MCP_PORT),
        "JC_WEB_PORT": str(GATEWAY_PORT),
        "XDG_DATA_HOME": "/app/data",
    }
    if getattr(settings, "NIM_API_KEY", ""):
        env["NVIDIA_API_KEY"] = settings.NIM_API_KEY
        env["NVIDIA_MODEL"] = getattr(settings, "NIM_MODEL", "meta/llama-3.1-8b-instruct")
    return [f"{k}={v}" for k, v in env.items()]


def _create_body() -> dict:
    def _binding(p: int) -> list[dict]:
        return [{"HostPort": str(p)}]

    return {
        "Image": IMAGE,
        "Env": _container_env(),
        "ExposedPorts": {
            f"{WEB_PORT}/tcp": {},
            f"{GATEWAY_PORT}/tcp": {},
            f"{MCP_PORT}/tcp": {},
        },
        "HostConfig": {
            "PortBindings": {
                f"{WEB_PORT}/tcp": _binding(WEB_HOST_PORT),
                f"{GATEWAY_PORT}/tcp": _binding(GATEWAY_PORT),
                f"{MCP_PORT}/tcp": _binding(MCP_PORT),
            },
            "RestartPolicy": {"Name": "unless-stopped"},
        },
        "NetworkingConfig": {"EndpointsConfig": {_detect_network(): {}}},
    }


def container_status() -> dict:
    """Return the current state of the JobCamelonapp container."""
    if not os.path.exists(UNIX_SOCKET):
        return {
            "running": False,
            "exists": False,
            "error": "Docker socket unavailable inside the backend container.",
            "url": _public_url(),
        }
    status, info = _docker_request("GET", f"/containers/{CONTAINER_NAME}/json")
    if status == 200:
        state = info.get("State", {}) or {}
        running = bool(state.get("Running"))
        return {
            "running": running,
            "exists": True,
            "status": state.get("Status") or ("running" if running else "exited"),
            "url": _public_url(),
            "image": (info.get("Config") or {}).get("Image"),
        }
    if status == 404:
        return {"running": False, "exists": False, "url": _public_url()}
    return {"running": False, "exists": False, "error": f"docker API error {status}: {info}"}


def start_container() -> dict:
    """Create and start a fresh JobCamelonapp container, or start an existing one."""
    if not os.path.exists(UNIX_SOCKET):
        return {
            "success": False,
            "error": (
                "The backend container cannot reach the Docker daemon. Add "
                "'/var/run/docker.sock:/var/run/docker.sock' to the backend service "
                "and run 'docker compose up -d backend'."
            ),
        }

    # 1. Image must exist.
    status, _ = _docker_request("GET", f"/images/{IMAGE}/json")
    if status == 404:
        return {
            "success": False,
            "error": (
                f"Image {IMAGE} is not built yet. Build it once from the repo root:\n"
                f"    docker build -t {IMAGE} ./JobCamelonapp"
            ),
        }
    if status != 200:
        return {"success": False, "error": f"docker image inspect failed ({status})."}

    # 2. Reuse an existing container if it is already running.
    status, info = _docker_request("GET", f"/containers/{CONTAINER_NAME}/json")
    if status == 200:
        if (info.get("State") or {}).get("Running"):
            return {"success": True, "already_running": True, "url": _public_url()}
        # Stale/stopped container from a previous run — remove so we always
        # start a NEW container as requested.
        _docker_request("DELETE", f"/containers/{CONTAINER_NAME}?force=true")
    elif status != 404:
        return {"success": False, "error": f"docker container inspect failed ({status})."}

    # 3. Create.
    status, created = _docker_request("POST", f"/containers/create?name={CONTAINER_NAME}", _create_body())
    if status not in (200, 201):
        return {"success": False, "error": f"docker create failed ({status}): {created}"}

    container_id = (created or {}).get("Id", CONTAINER_NAME)

    # 4. Start.
    status, started = _docker_request("POST", f"/containers/{container_id}/start")
    if status not in (200, 204):
        # Don't leave a half-created container behind (e.g. port already in use).
        _docker_request("DELETE", f"/containers/{container_id}?force=true")
        return {"success": False, "error": f"docker start failed ({status}): {started}"}

    return {
        "success": True,
        "container": CONTAINER_NAME,
        "url": _public_url(),
        "network": _detect_network(),
    }
