"""MCP bridge: connect two JobChameleon-family MCP servers to each other.

The dockerized ``jobchameleon`` microservice and the ``JobCamelonapp``
workbench each run an MCP-over-StreamableHTTP server. This module lets each
server ALSO expose the other server's tools (namespaced with a ``peer_``
prefix) so a single MCP client of either app can call both — connecting the
two apps via MCP.

Peer endpoint is configured per process via env:

* jobchameleon container  -> ``JCAPP_MCP_URL``  (points at JobCamelonapp)
* JobCamelonapp container -> ``JC_MCP_URL``     (points at jobchameleon)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

from mcp.server.mcpserver import MCPServer

_log = logging.getLogger(__name__)


def _result_text(result: Any) -> str:
    content = getattr(result, "content", None) or []
    text = "".join(
        item.text for item in content if getattr(item, "type", "") == "text"
    )
    if text:
        return text
    structured = getattr(result, "structured_content", None)
    if structured is not None:
        return json.dumps(structured, ensure_ascii=False, default=str)
    return json.dumps(result, ensure_ascii=False, default=str)


async def _call_peer(endpoint: str, tool_name: str, arguments: dict[str, Any]) -> str:
    from mcp.client.client import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    async with streamable_http_client(endpoint) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments or {})
            return _result_text(result)


def _wrapper_for(endpoint: str, tool_name: str):
    """Build a typed wrapper matching the peer tool's input schema.

    Both JobChameleon-family apps expose the same three job-intelligence tools,
    so we mirror their signatures exactly (better schema for MCP clients) and
    fall back to ``**kwargs`` for any future peer tool.
    """
    if tool_name == "score_job_fit":

        async def score_job_fit(posting: str, candidate: dict) -> str:
            return await _call_peer(endpoint, tool_name, {"posting": posting, "candidate": candidate})

        return score_job_fit

    if tool_name == "evaluate_lead_quality":

        async def evaluate_lead_quality(
            lead: dict,
            min_quality: int = 60,
            target_level: str = "beginner",
            max_age_days: int = 7,
        ) -> str:
            return await _call_peer(
                endpoint,
                tool_name,
                {
                    "lead": lead,
                    "min_quality": min_quality,
                    "target_level": target_level,
                    "max_age_days": max_age_days,
                },
            )

        return evaluate_lead_quality

    if tool_name == "extract_lead_intel":

        async def extract_lead_intel(text: str) -> str:
            return await _call_peer(endpoint, tool_name, {"text": text})

        return extract_lead_intel

    async def generic(**kwargs: Any) -> str:
        return await _call_peer(endpoint, tool_name, kwargs or {})

    return generic


def _list_peer_tools(endpoint: str) -> list[dict[str, Any]]:
    from mcp.client.client import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    async def _run() -> list[dict[str, Any]]:
        async with streamable_http_client(endpoint) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await session.initialize()
                tools = await session.list_tools()
                return [
                    {
                        "name": tool.name,
                        "title": getattr(tool, "title", None),
                        "description": getattr(tool, "description", None),
                    }
                    for tool in tools.tools
                ]

    return asyncio.run(_run())


def register_peer_tools(
    server: MCPServer,
    *,
    prefix: str,
    env_var: str,
    peer_name: str,
) -> list[str]:
    """Register the peer MCP server's tools on ``server`` under ``prefix<name>``.

    Returns the list of registered (namespaced) tool names. Skips registration
    (with a warning) when the peer endpoint is unset or unreachable, so a
    missing peer never prevents the local server from starting.
    """
    endpoint = os.environ.get(env_var, "").strip()
    if not endpoint:
        _log.info("MCP bridge: %s not set — no peer tools registered", env_var)
        return []

    try:
        peer_tools = _list_peer_tools(endpoint)
    except Exception as exc:  # noqa: BLE001 — bridge must never crash startup
        _log.warning("MCP bridge: cannot reach %s at %s: %s", peer_name, endpoint, exc)
        return []

    registered: list[str] = []
    for tool in peer_tools:
        name = tool.get("name") or ""
        if not name:
            continue
        peer_tool_name = f"{prefix}{name}"

        server.add_tool(
            _wrapper_for(endpoint, name),
            name=peer_tool_name,
            title=tool.get("title") or f"{peer_name} {name}",
            description=(
                tool.get("description")
                or f"Bridge to {peer_name}'s {name} MCP tool (remote call over MCP)."
            ),
        )
        registered.append(peer_tool_name)

    _log.info("MCP bridge: registered %s peer tool(s) from %s: %s", len(registered), peer_name, registered)
    return registered
