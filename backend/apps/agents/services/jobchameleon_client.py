"""
JobChameleon microservice client — REST proxy for the JobChameleon job-intelligence
gateway (health, leads, settings) plus an MCP passthrough helper.

JobChameleon shares ML-Auditor's NVIDIA NIM key/model via compose env, so any LLM
calls it makes use the same chat API key as ML-Auditor's chatbot.
"""

import json
import logging

import httpx

from django.conf import settings

logger = logging.getLogger(__name__)


def _base_url() -> str:
    return getattr(settings, "JC_URL", "http://localhost:8787").rstrip("/")


def _token() -> str:
    return getattr(settings, "JC_API_TOKEN", "")


def _headers() -> dict:
    return {"Authorization": f"Bearer {_token()}"}


def jobchameleon_health() -> dict:
    """GET /health (no auth required)."""
    try:
        resp = httpx.get(f"{_base_url()}/health", timeout=6)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning(f"jobchameleon health failed: {e}")
        return {"status": "error", "error": str(e)[:200]}


def jobchameleon_status() -> dict:
    """Health + settings summary for the UI card."""
    health = jobchameleon_health()
    result = {"connected": health.get("status") == "alive", "health": health}
    try:
        resp = httpx.get(f"{_base_url()}/api/v1/settings", headers=_headers(), timeout=6)
        resp.raise_for_status()
        settings_data = resp.json()
        result["llm_provider"] = settings_data.get("llm_provider")
        result["llm_model"] = settings_data.get("nvidia_model")
        result["llm_configured"] = bool(settings_data.get("llm_provider") == "nvidia")
    except Exception as e:
        result["settings_error"] = str(e)[:200]
    return result


def jobchameleon_leads(limit: int = 10) -> dict:
    """GET /api/v1/leads with the JobChameleon bearer token."""
    try:
        resp = httpx.get(
            f"{_base_url()}/api/v1/leads",
            headers=_headers(),
            params={"limit": limit},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        return {"leads": data if isinstance(data, list) else data.get("leads", []), "count": len(data) if isinstance(data, list) else 0}
    except Exception as e:
        logger.warning(f"jobchameleon leads failed: {e}")
        return {"error": str(e)[:200], "leads": [], "count": 0}


def jobchameleon_mcp_tool(tool: str, arguments: dict | None = None) -> dict:
    """Proxy an MCP call to the JobChameleon MCP endpoint."""
    from .mcp_client import call_jobchameleon_mcp

    try:
        text = call_jobchameleon_mcp(tool, arguments)
        if text.startswith("MCP call failed"):
            return {"success": False, "error": text}
        try:
            parsed = json.loads(text)
            return {"success": True, "result": parsed}
        except (TypeError, ValueError):
            return {"success": True, "result": text}
    except Exception as e:
        logger.warning(f"jobchameleon MCP tool {tool} failed: {e}")
        return {"success": False, "error": str(e)[:200]}
