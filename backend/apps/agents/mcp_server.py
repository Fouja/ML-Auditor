"""
ML-Auditor MCP server — exposes the agent's tools (tasks, notes, calendar,
live web search/fetch, news, Agent-Reach status) over the Model Context
Protocol. Any MCP client (Claude, Cursor, opencode, mcporter...) can connect.

Run (stdio):   python -m apps.agents.mcp_server
Run (HTTP):    python -m apps.agents.mcp_server --http --port 8100

The `agent_reach_get_status` tool also acts as an MCP *client*: it connects to
the Agent-Reach MCP endpoint served by the web-tools microservice.
"""

import argparse
import asyncio
import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from asgiref.sync import sync_to_async  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402
from django.utils import timezone  # noqa: E402

logger = logging.getLogger("mlauditor-mcp")


def _service_user():
    email = os.environ.get("ML_AUDITOR_MCP_USER_EMAIL", "test@test.com")
    user = get_user_model().objects.filter(email=email).first()
    if not user:
        raise RuntimeError(f"MCP service user {email!r} not found in database")
    return user


def _json(value) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, default=str, indent=2)
    except (TypeError, ValueError):
        return str(value)


def create_server():
    from mcp.server.mcpserver import MCPServer

    from apps.agents.services.tool_executor import ToolExecutor

    server = MCPServer(
        name="mlauditor",
        title="ML-Auditor",
        description=(
            "ML-Auditor assistant: tasks (Wall of Work), notes, calendar, live "
            "web search/fetch, recent news and Agent-Reach status."
        ),
        version="1.0.0",
    )

    executor = ToolExecutor(_service_user())

    @server.tool()
    async def mlauditor_status() -> str:
        """Overview of the ML-Auditor system: web-tools microservice health, LLM config, task/note/news counts."""
        from django.conf import settings

        from .services.web_tools_client import agent_reach_status

        def _counts():
            from apps.workspace.models import NewsArticle, Note, Task

            user = _service_user()
            return {
                "service_user": user.email,
                "tasks": Task.objects.filter(user=user).count(),
                "notes": Note.objects.filter(user=user).count(),
                "news_articles": NewsArticle.objects.filter(feed__user=user).count(),
            }

        counts = await sync_to_async(_counts)()
        result = {
            "service": "ML-Auditor MCP server",
            "version": "1.0.0",
            "service_user": counts.pop("service_user"),
            "web_tools_url": getattr(settings, "WEB_TOOLS_URL", "http://localhost:8090"),
            "counts": counts,
        }
        doctor = agent_reach_status()
        if isinstance(doctor, dict) and doctor.get("error"):
            result["agent_reach"] = {"error": doctor["error"]}
        else:
            result["agent_reach"] = {"status": "ok"}
        return _json(result)

    @server.tool()
    async def agent_reach_get_status() -> str:
        """Get Agent Reach status over MCP: which channels are installed and active (via the web-tools MCP client)."""
        from .services.mcp_client import call_agent_reach_get_status

        return await asyncio.to_thread(call_agent_reach_get_status)

    @server.tool()
    async def jobchameleon_score_fit(posting: str, candidate: dict) -> str:
        """Score a job posting against a candidate profile using JobChameleon's fit rubric."""
        from .services.mcp_client import call_jobchameleon_mcp

        return await asyncio.to_thread(
            call_jobchameleon_mcp, "score_job_fit", {"posting": posting, "candidate": candidate}
        )

    @server.tool()
    async def jobchameleon_evaluate_lead(
        lead: dict,
        min_quality: int = 60,
        target_level: str = "beginner",
        max_age_days: int = 7,
    ) -> str:
        """Run JobChameleon's lead quality gate before saving/ranking a job lead."""
        from .services.mcp_client import call_jobchameleon_mcp

        return await asyncio.to_thread(
            call_jobchameleon_mcp,
            "evaluate_lead_quality",
            {
                "lead": lead,
                "min_quality": min_quality,
                "target_level": target_level,
                "max_age_days": max_age_days,
            },
        )

    @server.tool()
    async def jobchameleon_extract_lead_intel(text: str) -> str:
        """Extract company, location, budget, urgency, stack, and signal quality from raw job/lead text."""
        from .services.mcp_client import call_jobchameleon_mcp

        return await asyncio.to_thread(
            call_jobchameleon_mcp, "extract_lead_intel", {"text": text}
        )

    @server.tool()
    async def jobchameleon_launch(provider: str = "gmail", open_in: str = "tab") -> str:
        """Launch the JOBchameleon app with the email OAuth2 provider connected.

        provider: 'gmail' | 'outlook' | 'yahoo' | 'custom' (connexion only, no email send).
        open_in:  'tab' opens the full app in a new browser tab; 'iframe' embeds it in ML-Auditor.

        Returns a JSON object: { url, token, email_connected, provider, open_in }.
        If the email provider is not connected, the response includes an oauth_url to start the flow.
        """
        from django.conf import settings
        from urllib.parse import quote

        def _status():
            user = _service_user()
            return {
                "email_connected": bool(getattr(user, "jc_email_connected", False)),
                "provider": getattr(user, "jc_email_provider", "") or "",
            }

        status = await sync_to_async(_status)()
        jc_url = (
            getattr(settings, "JC_PUBLIC_URL", None)
            or getattr(settings, "JC_URL", os.environ.get("JC_URL", "http://localhost:8787"))
        )
        token = getattr(settings, "JC_API_TOKEN", os.environ.get("JC_API_TOKEN", ""))
        result = {
            "url": jc_url,
            "token": token,
            "email_connected": status["email_connected"],
            "provider": status["provider"] or provider,
            "open_in": open_in,
        }
        if not status["email_connected"] and provider == "gmail":
            client_id = getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "")
            redirect_uri = getattr(
                settings,
                "GOOGLE_OAUTH_REDIRECT_URI",
                "http://localhost:8000/api/integrations/oauth/google/callback",
            )
            scopes = ["https://www.googleapis.com/auth/gmail.readonly"]
            result["oauth_url"] = (
                "https://accounts.google.com/o/oauth2/v2/auth?"
                f"client_id={client_id}&redirect_uri={quote(redirect_uri, safe='')}&"
                f"response_type=code&scope={quote(' '.join(scopes))}&"
                f"access_type=offline&prompt=consent&state={status.get('user_id', '')}"
            )
        return _json(result)

    @server.tool()
    async def web_search(query: str, num_results: int = 5) -> str:
        """Search the live web (DuckDuckGo keyless or Exa if configured)."""
        result = await executor.execute("web_search", {"query": query, "num_results": num_results})
        return _json(result)

    @server.tool()
    async def fetch_webpage(url: str) -> str:
        """Fetch a URL and return clean markdown (Jina Reader)."""
        result = await executor.execute("fetch_webpage", {"url": url})
        return _json(result)

    @server.tool()
    async def get_recent_news(days: int = 7, count: int = 15) -> str:
        """Get the latest articles from the user's news feeds."""
        result = await executor.execute("get_recent_news", {"days": days, "count": count})
        return _json(result)

    @server.tool()
    async def list_tasks(status: str = "") -> str:
        """List tasks on the Wall of Work board, optionally filtered by status (todo/in_progress/review/done)."""
        from apps.workspace.models import Task

        def _list():
            qs = Task.objects.filter(user=_service_user()).order_by("position")
            if status:
                qs = qs.filter(status=status)
            return list(qs[:50])

        tasks = await sync_to_async(_list)()
        return _json(
            [
                {
                    "id": str(t.id),
                    "title": t.title,
                    "status": t.status,
                    "priority": t.priority,
                    "due_date": t.due_date.isoformat() if t.due_date else None,
                    "tags": t.tags,
                }
                for t in tasks
            ]
        )

    @server.tool()
    async def create_task(
        title: str,
        status: str = "todo",
        priority: str = "medium",
        description: str = "",
    ) -> str:
        """Create a new task on the Wall of Work board."""
        result = await executor.execute(
            "create_task",
            {
                "title": title,
                "status": status,
                "priority": priority,
                "description": description,
            },
        )
        return _json(result)

    @server.tool()
    async def list_notes(format: str = "", query: str = "") -> str:
        """List or search notes (optionally by format or keyword)."""
        result = await executor.execute(
            "get_notes", {"format": format or None, "query": query or None}
        )
        return _json(result)

    @server.tool()
    async def create_note(title: str, content: str = "", format: str = "note", tags: str = "") -> str:
        """Create a new note. Tags: comma-separated string."""
        result = await executor.execute(
            "create_note",
            {
                "title": title,
                "content": content,
                "format": format,
                "tags": [t.strip() for t in tags.split(",") if t.strip()],
            },
        )
        return _json(result)

    @server.tool()
    async def list_calendar_events(days: int = 14) -> str:
        """List upcoming calendar events for the next N days."""
        from apps.workspace.models import CalendarEvent

        def _list():
            now = timezone.now()
            return list(
                CalendarEvent.objects.filter(
                    user=_service_user(), start_time__gte=now,
                    start_time__lte=now + timezone.timedelta(days=max(1, days)),
                ).order_by("start_time")[:50]
            )

        events = await sync_to_async(_list)()
        return _json(
            [
                {
                    "id": str(e.id),
                    "title": e.title,
                    "start_time": e.start_time.isoformat(),
                    "end_time": e.end_time.isoformat(),
                    "location": e.location,
                    "color": e.color,
                }
                for e in events
            ]
        )

    @server.tool()
    async def create_calendar_event(title: str, start_time: str, end_time: str, description: str = "") -> str:
        """Create a calendar event. Times must be ISO 8601 (e.g. 2026-08-10T09:00:00Z)."""
        result = await executor.execute(
            "create_calendar_event",
            {
                "title": title,
                "description": description,
                "start_time": start_time,
                "end_time": end_time,
            },
        )
        return _json(result)

    return server


def main():
    parser = argparse.ArgumentParser(description="ML-Auditor MCP server")
    parser.add_argument("--http", action="store_true", help="run over StreamableHTTP instead of stdio")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8100)
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING)

    server = create_server()
    if args.http:
        asyncio.run(server.run_streamable_http_async(host=args.host, port=args.port))
    else:
        asyncio.run(server.run_stdio_async())


if __name__ == "__main__":
    main()
