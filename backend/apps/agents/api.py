"""
Agent API endpoints for ML-Auditor.
Chat, workflows, voice, notifications.
"""

import asyncio
from typing import Any, Dict, Optional

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


# ─── Chat ────────────────────────────────────────────────────────────


@router.post("/chat", response=AgentResponse)
def chat_with_agent(request, payload: AgentMessage):
    """Send message to AI agent with tool execution."""
    from .services.agent_command import AgentCommandService, ConversationStore

    user = request.auth
    agent_type = payload.agent_type or "general"

    # Get conversation history
    history = ConversationStore.get_history(str(user.id), agent_type)

    # Process message
    service = AgentCommandService(user)
    result = asyncio.run(
        service.process_message(
            content=payload.content,
            agent_type=agent_type,
            conversation_history=history,
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
        metadata=result.get("metadata"),
    )


@router.delete("/chat/history")
def clear_chat_history(request, agent_type: str = Query("general")):
    """Clear conversation history for an agent."""
    from .services.agent_command import ConversationStore

    user = request.auth
    ConversationStore.clear(str(user.id), agent_type)
    return {"success": True}


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
