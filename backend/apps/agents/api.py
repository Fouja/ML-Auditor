"""
Agent API endpoints for ML-Auditor.
Chat, workflows, voice, notifications.
"""

import asyncio
from typing import Any, Dict, List, Optional

from django.core.cache import cache
from ninja import Query, Router
from pydantic import BaseModel

from .schemas import AgentMessage, AgentResponse, AgentStatus

router = Router()


# ─── Schemas ─────────────────────────────────────────────────────────


class WorkflowRequestSchema(BaseModel):
    workflow: str
    data: Dict[str, Any]


class NotificationPrefsSchema(BaseModel):
    email_notifications: Optional[bool] = None
    push_notifications: Optional[bool] = None
    webhook_url: Optional[str] = None


class VoiceCommandSchema(BaseModel):
    audio_data: str
    format: str = "webm"


class ExecuteToolSchema(BaseModel):
    tool: str
    args: Dict[str, Any] = {}


class WebToolsSearchSchema(BaseModel):
    query: str
    num_results: int = 5


class WebToolsUrlSchema(BaseModel):
    url: str


class JobChameleonMcpSchema(BaseModel):
    tool: str
    arguments: dict | None = None


class FeedbackSchema(BaseModel):
    rating: int
    comment: str = ""
    agent_type: str = "general"
    user_message: str = ""
    agent_response: str = ""
    tool_calls: Optional[List[Dict[str, Any]]] = None


# ─── Chat ────────────────────────────────────────────────────────────


@router.post("/chat", response=AgentResponse)
def chat_with_agent(request, payload: AgentMessage):
    """Send message to AI agent with tool execution."""
    from .services.agent_command import AgentCommandService, ConversationStore

    user = request.auth
    agent_type = payload.agent_type or "general"

    # Get conversation history
    history = ConversationStore.get_history(str(user.id), agent_type)

    studio_settings = {
        "creativity": payload.creativity,
        "creativity_level": payload.creativity_level,
        "context_depth": payload.context_depth,
        "token_budget": payload.token_budget,
    }

    # Process message
    service = AgentCommandService(user)
    result = asyncio.run(
        service.process_message(
            content=payload.content,
            agent_type=agent_type,
            conversation_history=history,
            studio_settings=studio_settings,
        )
    )

    # Store conversation
    ConversationStore.add_message(str(user.id), agent_type, "user", payload.content)
    ConversationStore.add_message(
        str(user.id), agent_type, "assistant", result["response"]
    )

    return AgentResponse(
        response=result["response"],
        agent_type=result["agent_type"],
        actions_taken=result["actions_taken"],
        tool_calls=result.get("tool_calls", []),
        pending_actions=result.get("pending_actions", []),
        metadata=result.get("metadata"),
    )


@router.post("/execute-tool")
def execute_confirmed_tool(request, payload: ExecuteToolSchema):
    """Execute a write tool that the user explicitly confirmed.

    Write tools are never auto-run by the agent; the frontend asks the user to
    confirm a proposed action, then calls this endpoint to run it.
    """
    from .services.agent_command import AgentCommandService, WRITE_TOOLS

    if payload.tool not in WRITE_TOOLS:
        return {"success": False, "error": "Only confirmed write tools can be executed here."}

    service = AgentCommandService(request.auth)
    executor = service._get_tool_executor()
    result = asyncio.run(executor.execute(payload.tool, payload.args or {}))
    return {"success": bool(result.get("success", False)), "result": result}


@router.get("/llm/health")
def llm_health(request):
    """Live LLM/NIM health check — pings the configured model and returns latency."""
    import logging
    import time

    import httpx
    from django.conf import settings

    from .services.agent_command import AgentCommandService

    llm_logger = logging.getLogger("apps.logs.llm")

    service = AgentCommandService(request.auth)
    api_key, base_url, model, _provider = asyncio.run(service._get_nim_config())
    if not api_key:
        llm_logger.warning(
            "llm_health_not_configured",
            extra={
                "service": "llm",
                "stack": "django",
                "metrics": {
                    "metric": "llm_health",
                    "metric_type": "llm",
                    "event_type": "health_check",
                    "status": "not_configured",
                    "latency_ms": 0,
                    "model": model,
                },
            },
        )
        return {"status": "not_configured", "model": model, "latency_ms": 0}

    status = "error"
    latency_ms = 0
    error = ""
    try:
        start = time.monotonic()
        with httpx.Client(timeout=20) as client:
            resp = client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "user", "content": "Reply with the single word: ok"}
                    ],
                    "max_tokens": 5,
                },
            )
            latency_ms = round((time.monotonic() - start) * 1000)
            resp.raise_for_status()
            status = "ok"
    except Exception as e:
        error = str(e)[:300]

    llm_logger.info(
        "llm_health",
        extra={
            "service": "llm",
            "stack": "django",
            "metrics": {
                "metric": "llm_health",
                "metric_type": "llm",
                "event_type": "health_check",
                "status": status,
                "latency_ms": latency_ms,
                "model": model,
                "error": error,
            },
        },
    )
    return {"status": status, "model": model, "latency_ms": latency_ms, "error": error}


# ─── Web Tools microservice (Agent-Reach) ────────────────────────────


def _web_tools_health(base_url: str) -> dict:
    import httpx

    async def _fetch():
        async with httpx.AsyncClient(timeout=6) as client:
            resp = await client.get(f"{base_url}/health")
            resp.raise_for_status()
            return resp.json()

    return asyncio.run(_fetch())


@router.get("/web-tools/status")
def web_tools_status(request):
    """Live status of the Web Tools microservice (Agent-Reach + search/RSS) and the MCP endpoints."""
    from concurrent.futures import ThreadPoolExecutor

    from django.conf import settings

    from .services import web_tools_client
    from .services.mcp_client import call_agent_reach_get_status

    base_url = getattr(settings, "WEB_TOOLS_URL", "http://localhost:8090")

    def _doctor():
        return asyncio.run(web_tools_client.agent_reach_status())

    def _probe_mcp_server():
        async def _probe():
            from mcp.client.client import ClientSession
            from mcp.client.streamable_http import streamable_http_client

            async with streamable_http_client("http://mcp-server:8100/mcp") as (r, w):
                async with ClientSession(r, w) as s:
                    await s.initialize()
                    tools = await s.list_tools()
                    return {"connected": True, "tools": len(tools.tools)}

        return asyncio.run(_probe())

    result = {
        "connected": False,
        "service_url": base_url,
        "health": None,
        "doctor": None,
    }

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            pool.submit(_web_tools_health, base_url): "health",
            pool.submit(_doctor): "doctor",
            pool.submit(_probe_mcp_server): "mcp",
            pool.submit(call_agent_reach_get_status, base_url): "agent_reach_mcp",
        }
        for future, key in futures.items():
            try:
                value = future.result()
            except Exception as e:
                value = None
                if key == "health":
                    result["error"] = str(e)[:300]
                else:
                    result[f"{key}_error"] = str(e)[:200]

            if key == "health" and value is not None:
                result["health"] = value
                result["connected"] = True
            elif key == "doctor" and value is not None:
                result["doctor"] = str(value)[:1500]
            elif key == "mcp":
                result["mcp"] = value or {"connected": False}
            elif key == "agent_reach_mcp":
                result["agent_reach_mcp"] = {
                    "connected": bool(value) and "MCP call failed" not in value,
                    "status": (value or "")[:1500],
                }
    return result


@router.post("/web-tools/search")
def web_tools_search(request, payload: WebToolsSearchSchema):
    """Proxy a live web search through the Web Tools microservice."""
    from .services.web_tools_client import web_search

    if not payload.query.strip():
        return {"query": "", "results": "", "error": "query is required"}
    return {
        "query": payload.query,
        "results": asyncio.run(web_search(payload.query, payload.num_results)),
    }


@router.post("/web-tools/fetch")
def web_tools_fetch(request, payload: WebToolsUrlSchema):
    """Proxy a URL fetch through the Web Tools microservice (Jina Reader)."""
    from .services.web_tools_client import fetch_webpage

    if not payload.url.startswith(("http://", "https://")):
        return {"url": payload.url, "error": "url must start with http:// or https://"}
    return {"url": payload.url, "markdown": asyncio.run(fetch_webpage(payload.url))}


# ─── JobChameleon microservice (job intelligence) ────────────────────


@router.get("/jobchameleon/status")
def jobchameleon_status(request):
    """Live status of the JobChameleon microservice + its LLM (NVIDIA NIM) config."""
    from .services import jobchameleon_client

    result = jobchameleon_client.jobchameleon_status()

    # MCP reachability + available tools
    try:
        async def _probe():
            from mcp.client.client import ClientSession
            from mcp.client.streamable_http import streamable_http_client
            from django.conf import settings

            async with streamable_http_client(getattr(settings, "JC_MCP_URL", "http://localhost:8788/mcp")) as (r, w):
                async with ClientSession(r, w) as s:
                    await s.initialize()
                    tools = await s.list_tools()
                    return {"connected": True, "tools": [t.name for t in tools.tools]}

        result["mcp"] = asyncio.run(_probe())
    except Exception as e:
        result["mcp"] = {"connected": False, "error": str(e)[:200]}
    return result


@router.get("/jobchameleon/leads")
def jobchameleon_leads(request, limit: int = Query(10, ge=1, le=50)):
    """List leads from the JobChameleon microservice."""
    from .services import jobchameleon_client

    return jobchameleon_client.jobchameleon_leads(limit=limit)


@router.post("/jobchameleon/mcp")
def jobchameleon_mcp(request, payload: JobChameleonMcpSchema):
    """Call a JobChameleon MCP tool (score_job_fit / evaluate_lead_quality / extract_lead_intel)."""
    from .services import jobchameleon_client

    if payload.tool not in {"score_job_fit", "evaluate_lead_quality", "extract_lead_intel"}:
        return {"success": False, "error": f"unsupported tool: {payload.tool}"}
    return jobchameleon_client.jobchameleon_mcp_tool(payload.tool, payload.arguments)


@router.get("/jobcamelonapp/status")
def jobcamelonapp_status(request):
    """Live status of the JobCamelonapp workbench container (run on demand)."""
    from .services.jobcamelonapp_container import container_status

    return container_status()


@router.post("/jobcamelonapp/start")
def jobcamelonapp_start(request):
    """Create and run a new Docker container from the JobCamelonapp codebase.

    The container runs the full JobChameleon workbench (FastAPI gateway on
    1403, MCP on 8790, web UI on 8088) on the ML-Auditor compose network and
    is linked to the jobchameleon microservice over MCP.
    """
    from .services.jobcamelonapp_container import start_container

    return start_container()


@router.get("/jobchameleon/launch")
def jobchameleon_launch(request):
    """Return the JOBchameleon launch URL + bearer token + the user's OAuth2 email connexion state.

    Connexion only — never publishes OAuth email secrets to JOBchameleon; the front-end opens the
    app pre-authorised by the user's email connexion flag set during Google OAuth callback.

    The full workbench (JobCamelonapp container) is started on demand if it isn't running yet, and
    the URL returned here points at its browser-facing web UI (``JCAPP_PUBLIC_URL``, default
    ``http://localhost:8089`` — host port 8088 may be taken by the Wekan snap's FerretDB). The
    gateway microservice console stays reachable via ``JC_PUBLIC_URL``.
    """
    from django.conf import settings

    from .services.jobcamelonapp_container import start_container

    user = request.auth
    workbench = start_container()
    if not workbench.get("success"):
        return {
            "success": False,
            "error": workbench.get("error", "JobCamelonapp workbench could not be started."),
            "console_url": (
                getattr(settings, "JC_PUBLIC_URL", None)
                or getattr(settings, "JC_URL", "http://localhost:8787")
            ),
        }
    public_url = (
        getattr(settings, "JCAPP_PUBLIC_URL", None)
        or getattr(settings, "JC_URL", "http://localhost:8089")
    )
    return {
        "url": public_url,
        "token": getattr(settings, "JC_API_TOKEN", ""),
        "email_connected": bool(getattr(user, "jc_email_connected", False)),
        "provider": getattr(user, "jc_email_provider", "") or "",
        "workbench": workbench.get("container") or "",
        "oauth_google_url": (
            f"http://localhost:8000/api/integrations/oauth/google"
            if not getattr(user, "jc_email_connected", False)
            else None
        ),
    }


@router.post("/feedback")
def submit_feedback(request, payload: FeedbackSchema):
    """Record human feedback (rating/comment) for an agent response."""
    from .services.feedback_service import submit_feedback

    if not 1 <= payload.rating <= 5:
        return {"success": False, "error": "rating must be between 1 and 5"}

    result = submit_feedback(
        user_id=str(request.auth.id),
        rating=payload.rating,
        comment=payload.comment,
        agent_type=payload.agent_type,
        user_message=payload.user_message,
        agent_response=payload.agent_response,
        tool_calls=payload.tool_calls or [],
    )
    if "error" in result:
        return {"success": False, "error": result["error"]}
    return {"success": True, "id": result.get("id"), "sentiment": result.get("sentiment")}


@router.delete("/chat/history")
def clear_chat_history(request, agent_type: str = Query("general")):
    """Clear conversation history for an agent."""
    from .services.agent_command import ConversationStore

    user = request.auth
    ConversationStore.clear(str(user.id), agent_type)
    return {"success": True}


@router.get("/chat/history")
def chat_history(request, agent_type: str = Query("general"), limit: int = Query(50)):
    """Get the persisted conversation history for an agent."""
    from .services.agent_command import ConversationStore

    user = request.auth
    history = ConversationStore.get_history(str(user.id), agent_type)
    conversations = ConversationStore.list_conversations(user, limit=limit)
    return {
        "agent_type": agent_type,
        "messages": history[-limit:],
        "conversations": conversations,
    }


# ─── Agent Status ────────────────────────────────────────────────────


@router.get("/status", response=AgentStatus)
def get_agent_status(request):
    """Get status of all agents."""
    cached = cache.get("agent_status")
    if cached:
        return AgentStatus(**cached)
    result = AgentStatus(
        agents=[
            {
                "name": "General Agent",
                "type": "general",
                "status": "ready",
                "description": "Main assistant for all tasks",
            },
            {
                "name": "Email Agent",
                "type": "email",
                "status": "ready",
                "description": "Classifies and manages emails",
            },
            {
                "name": "Financial Agent",
                "type": "financial",
                "status": "ready",
                "description": "Monitors transactions and anomalies",
            },
            {
                "name": "Calendar Agent",
                "type": "calendar",
                "status": "ready",
                "description": "Manages appointments and events",
            },
            {
                "name": "Kijiji Agent",
                "type": "kijiji",
                "status": "ready",
                "description": "Searches and negotiates deals",
            },
            {
                "name": "Canva Agent",
                "type": "canva",
                "status": "ready",
                "description": "Design management and competitor monitoring",
            },
        ],
        active_tasks=0,
        completed_tasks=0,
    )
    cache.set("agent_status", result.dict(), timeout=60)
    return result


# ─── Workflows ───────────────────────────────────────────────────────


@router.post("/workflows/execute")
def execute_workflow(request, payload: WorkflowRequestSchema):
    """Execute a smart workflow."""
    from .services.workflows import execute_workflow

    user = request.auth
    result = execute_workflow(payload.workflow, user, payload.data)
    return result.to_dict()


@router.get("/workflows")
def list_workflows(request):
    """List available workflows."""
    cached = cache.get("workflows_list")
    if cached:
        return cached
    from .services.workflows import WORKFLOWS

    result = {
        "workflows": [
            {"name": name, "description": handler.__doc__ or ""}
            for name, handler in WORKFLOWS.items()
        ]
    }
    cache.set("workflows_list", result, timeout=300)
    return result


# ─── Voice ───────────────────────────────────────────────────────────


@router.post("/voice")
def process_voice_command(request, payload: VoiceCommandSchema):
    """Process voice command via Whisper (placeholder)."""
    return {
        "response": "Voice processing requires Whisper API integration. Coming soon.",
        "agent_type": "voice",
        "status": "not_implemented",
    }


# ─── Notifications ───────────────────────────────────────────────────


@router.get("/notifications/preferences")
def get_notification_prefs(request):
    """Get user notification preferences."""
    from .services.notifications import NotificationPreferences

    user = request.auth
    return NotificationPreferences.get_preferences(user)


@router.put("/notifications/preferences")
def update_notification_prefs(request, payload: NotificationPrefsSchema):
    """Update user notification preferences."""
    from .services.notifications import NotificationPreferences

    user = request.auth
    prefs = {k: v for k, v in payload.dict().items() if v is not None}
    return NotificationPreferences.update_preferences(user, prefs)


@router.post("/notifications/test")
def test_notification(request):
    """Send a test notification."""
    from .services.notifications import AlertRouter

    user = request.auth
    result = AlertRouter.send_notification(
        user,
        {
            "title": "Test Notification",
            "description": "This is a test notification from ML-Auditor.",
            "severity": "low",
        },
    )
    return {"sent": result}
