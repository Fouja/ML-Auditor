"""
Pydantic schemas for Agent API.
"""

from typing import Any, Dict, List, Optional

from ninja import Schema


class AgentMessage(Schema):
    """Schema for agent message."""

    content: str
    agent_type: Optional[str] = "general"


class AgentResponse(Schema):
    """Schema for agent response."""

    response: str
    agent_type: str
    actions_taken: List[Dict[str, Any]] = []
    metadata: Optional[Dict[str, Any]] = None


class AgentStatus(Schema):
    """Schema for agent status."""

    agents: List[Dict[str, Any]]
    active_tasks: int
    completed_tasks: int


class VoiceCommand(Schema):
    """Schema for voice command."""

    audio_data: str  # Base64 encoded audio
    format: str = "webm"
