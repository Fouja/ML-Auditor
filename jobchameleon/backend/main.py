# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Vasudev Siddh and vasu-devs

from __future__ import annotations

import argparse
import asyncio
import os
import queue
import socket
import sys
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket

from api.app import create_app
from api.auth import create_api_token, require_ws_token
from api.scheduler import create_ghost_tick, create_lifespan, create_scheduler
from api.websocket import ConnectionManager, agent_event_action as _agent_event_action  # noqa: F401
from core.logging import get_logger
from llm.client import set_llm_event_callback

_log = get_logger(__name__)

# Load .env file from project root (2 levels up from backend/)
try:
    from dotenv import load_dotenv as _load_dotenv
    _env_path = Path(__file__).resolve().parent.parent / ".env"
    if _env_path.is_file():
        _load_dotenv(_env_path, override=False)
except Exception:
    pass


def _reserve_socket(preferred: int = 0) -> socket.socket:
    """Bind and KEEP OPEN a listening socket so the port can't be stolen.

    The old flow picked a port (bind+close) then let uvicorn re-bind it later,
    leaving a window where another process could grab the port — after we'd
    already announced it to the UI. Holding the open socket and handing it to
    uvicorn eliminates that TOCTOU race: the port is ours from announce to serve.
    """
    # No SO_REUSEADDR: we hand this exact socket to uvicorn (never re-bind), and
    # on Windows SO_REUSEADDR would let another process bind the same port,
    # defeating the whole point of reserving it. Keep the bind exclusive.
    # ML-Auditor container integration: bind 0.0.0.0 when JC_HOST is set so
    # other containers can reach this gateway.
    host = os.environ.get("JC_HOST") or os.environ.get("JHM_HOST") or "127.0.0.1"
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((host, preferred))
    return s


_UP = time.monotonic()
_sched = create_scheduler()
_API_TOKEN: str = create_api_token()
cm = ConnectionManager()

# Thread-safe queue bridging LLM thread-pool events → asyncio WebSocket broadcasts.
_llm_event_queue: queue.Queue = queue.Queue()


def _llm_event_handler(event_type: str, msg: str, step: str | None = None) -> None:
    """Called from LLM thread pool; enqueues event for async WebSocket broadcast."""
    _llm_event_queue.put({"event": event_type, "msg": msg, "step": step or ""})


async def _drain_llm_event_queue() -> None:
    """Background task: drain LLM event queue → WebSocket broadcast."""
    while True:
        try:
            while True:
                item = _llm_event_queue.get_nowait()
                await cm.broadcast({
                    "type": "agent",
                    "event": item["event"],
                    "msg": item["msg"],
                    "step": item["step"],
                })
        except queue.Empty:
            pass
        await asyncio.sleep(0.25)


async def _require_ws_token(ws: WebSocket) -> bool:
    return await require_ws_token(ws, lambda: _API_TOKEN)


def build_gateway_app():
    set_llm_event_callback(_llm_event_handler)
    ghost_tick = create_ghost_tick(cm)
    _lifespan = create_lifespan(_sched, ghost_tick, _log)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        drain_task = asyncio.create_task(_drain_llm_event_queue())
        async with _lifespan(app):
            yield
        drain_task.cancel()
        try:
            await drain_task
        except asyncio.CancelledError:
            pass

    return create_app(
        lifespan=lifespan,
        token_getter=lambda: _API_TOKEN,
        started_at=_UP,
        scheduler=_sched,
        ghost_tick=ghost_tick,
        connection_manager=cm,
        logger=_log,
        websocket_token_guard=_require_ws_token,
    )


_GATEWAY_APP_SINGLETON = None


def __getattr__(name: str):
    """Lazily build the gateway app on first attribute access (PEP 562).

    Building at module import time created a second app + scheduler that
    uvicorn never ran (it builds its own in ``__main__``), leaking resources
    and calling ``ensure_ghost_job``/``init_sql`` twice. Tests and tooling that
    do ``from main import app`` still work, but the app is only constructed
    once, on demand, and cached.
    """
    global _GATEWAY_APP_SINGLETON
    if name == "app":
        if _GATEWAY_APP_SINGLETON is None:
            _GATEWAY_APP_SINGLETON = build_gateway_app()
        return _GATEWAY_APP_SINGLETON
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _parse_args():
    parser = argparse.ArgumentParser(description="JustHireMe backend gateway runner")
    parser.add_argument("--port", type=int, default=0)
    # Accepted for backward compatibility: the desktop shell still passes it.
    # The app is always the in-process monolith now (no service subprocesses).
    parser.add_argument("--no-services", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    import uvicorn

    args = _parse_args()
    gateway_app = build_gateway_app()
    # Hold the bound socket, announce the port only after we own it, then hand
    # the same socket to uvicorn — no re-bind, no port-steal race.
    sock = _reserve_socket(args.port)
    port = sock.getsockname()[1]
    sys.stdout.write(f"JHM_TOKEN={_API_TOKEN}\n")
    sys.stdout.write(f"PORT:{port}\n")
    sys.stdout.flush()
    uvicorn.Server(uvicorn.Config(gateway_app, log_level="warning")).run(sockets=[sock])
