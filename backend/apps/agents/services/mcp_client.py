"""
MCP client — lets ML-Auditor act as a Model Context Protocol *client* and
consume external MCP servers. Currently connects to:

  * Agent-Reach MCP endpoint served by the web-tools microservice (get_status)
  * JobChameleon MCP endpoint served by the jobchameleon microservice
    (score_job_fit, evaluate_lead_quality, extract_lead_intel)
"""

import asyncio
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def _extract_text(result) -> str:
    """Best-effort extraction of text from an MCP CallToolResult."""
    content = getattr(result, "content", None)
    if isinstance(content, list):
        parts = []
        for item in content:
            text = getattr(item, "text", None)
            if text:
                parts.append(text)
        if parts:
            return "\n".join(parts)
    if isinstance(result, dict) and result.get("content"):
        parts = []
        for item in result["content"]:
            text = item.get("text") if isinstance(item, dict) else None
            if text:
                parts.append(text)
        if parts:
            return "\n".join(parts)
    return str(result)


async def _call_agent_reach_get_status_async(base_url: str | None = None) -> str:
    from mcp.client.client import ClientSession
    from mcp.client.streamable_http import streamable_http_client
    from urllib.parse import urlsplit, urlunsplit

    url = (base_url or getattr(settings, "WEB_TOOLS_URL", "http://localhost:8090")).rstrip("/")
    parts = urlsplit(url)
    host = parts.hostname or "web-tools"
    scheme = parts.scheme or "http"
    mcp_url = urlunsplit((scheme, f"{host}:8091", "/mcp", "", ""))
    try:
        async with streamable_http_client(mcp_url) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool("get_status", {})
                return _extract_text(result)
    except Exception as e:
        logger.warning(f"agent-reach MCP call failed: {e}")
        return f"MCP call failed: {e}"


def call_agent_reach_get_status(base_url: str | None = None) -> str:
    """Synchronous wrapper — spawn a fresh loop so it can be used from any thread."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            new_loop = asyncio.new_event_loop()
            try:
                return new_loop.run_until_complete(
                    _call_agent_reach_get_status_async(base_url)
                )
            finally:
                new_loop.close()
        return loop.run_until_complete(_call_agent_reach_get_status_async(base_url))
    except RuntimeError:
        new_loop = asyncio.new_event_loop()
        try:
            return new_loop.run_until_complete(
                _call_agent_reach_get_status_async(base_url)
            )
        finally:
            new_loop.close()


async def _call_mcp_tool_async(mcp_url: str, tool: str, arguments: dict) -> str:
    from mcp.client.client import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    try:
        async with streamable_http_client(mcp_url) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(tool, arguments or {})
                return _extract_text(result)
    except Exception as e:
        logger.warning(f"MCP call failed for {tool} at {mcp_url}: {e}")
        return f"MCP call failed: {e}"


def call_mcp_tool(mcp_url: str, tool: str, arguments: dict | None = None) -> str:
    """Synchronous MCP tool call against an arbitrary StreamableHTTP endpoint."""
    async def _run():
        return await _call_mcp_tool_async(mcp_url, tool, arguments or {})

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            new_loop = asyncio.new_event_loop()
            try:
                return new_loop.run_until_complete(_run())
            finally:
                new_loop.close()
        return loop.run_until_complete(_run())
    except RuntimeError:
        new_loop = asyncio.new_event_loop()
        try:
            return new_loop.run_until_complete(_run())
        finally:
            new_loop.close()


def call_jobchameleon_mcp(tool: str, arguments: dict | None = None) -> str:
    """Call a JobChameleon MCP tool (score_job_fit / evaluate_lead_quality / extract_lead_intel)."""
    mcp_url = getattr(settings, "JC_MCP_URL", "http://localhost:8788/mcp")
    return call_mcp_tool(mcp_url, tool, arguments)
