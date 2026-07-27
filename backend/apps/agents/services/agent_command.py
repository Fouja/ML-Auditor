"""
Agent command service — orchestrates CrewAI agents via NIM.
Routes user messages to the right agent, handles tool calls, and returns structured responses.
"""

import json
import logging
from typing import Any, Dict, List, Optional

import httpx

from django.conf import settings

logger = logging.getLogger(__name__)

NIM_BASE_URL = getattr(settings, "NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
NIM_MODEL = getattr(settings, "NIM_MODEL", "meta/llama-3.3-70b-instruct")
NIM_API_KEY = getattr(settings, "NIM_API_KEY", "")
ML_SERVICE_URL = getattr(settings, "ML_SERVICE_URL", "http://localhost:8001")


# ─── Agent definitions ───────────────────────────────────────────────

AGENT_SYSTEM_PROMPTS = {
    "general": (
        "You are ML-Auditor, an AI assistant that helps manage emails, calendar, "
        "banking, and marketplace activities. You can create tasks, send emails, "
        "analyze financial data, and negotiate on Kijiji. Always confirm before "
        "taking important actions."
    ),
    "email": (
        "You are the Email Agent. You classify, prioritize, and respond to emails. "
        "You can draft replies, categorize messages, and flag important threads."
    ),
    "financial": (
        "You are the Financial Agent. You monitor bank transactions, detect anomalies, "
        "and provide spending insights. You flag suspicious activity and suggest budget "
        "adjustments."
    ),
    "calendar": (
        "You are the Calendar Agent. You manage appointments, suggest optimal meeting "
        "times, and handle booking confirmations."
    ),
    "kijiji": (
        "You are the Kijiji Agent. You search listings, analyze deals, negotiate prices, "
        "and track marketplace activity. You can draft messages to sellers."
    ),
    "canva": (
        "You are the Canva Agent. You manage designs, monitor competitor trends, "
        "and suggest design improvements based on market analysis."
    ),
}

# Available tools for function calling
AVAILABLE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_task",
            "description": "Create a new task on the Wall of Work board",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Task title"},
                    "status": {"type": "string", "enum": ["todo", "in_progress", "review", "done"]},
                    "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                    "description": {"type": "string"},
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": "Send an email to a recipient",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient email"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"},
                    "cc": {"type": "string"},
                },
                "required": ["to", "subject", "body"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_calendar_event",
            "description": "Create a calendar event",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "start_time": {"type": "string", "description": "ISO datetime"},
                    "end_time": {"type": "string", "description": "ISO datetime"},
                    "description": {"type": "string"},
                    "location": {"type": "string"},
                },
                "required": ["summary", "start_time", "end_time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_kijiji",
            "description": "Search Kijiji listings",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "location": {"type": "string"},
                    "min_price": {"type": "number"},
                    "max_price": {"type": "number"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_transactions",
            "description": "Analyze recent bank transactions for anomalies",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "description": "Number of days to analyze"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_email",
            "description": "Search emails by query",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "folder": {"type": "string"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "draft_email_reply",
            "description": "Draft a reply to an email",
            "parameters": {
                "type": "object",
                "properties": {
                    "original_subject": {"type": "string"},
                    "original_from": {"type": "string"},
                    "draft_body": {"type": "string"},
                    "tone": {"type": "string", "enum": ["professional", "friendly", "formal", "casual"]},
                },
                "required": ["original_subject", "draft_body"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "canva_competitor_monitor",
            "description": "Monitor Canva design trends for competitor keywords",
            "parameters": {
                "type": "object",
                "properties": {
                    "keywords": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["keywords"],
            },
        },
    },
]


class AgentCommandService:
    """
    Main orchestrator for agent commands.
    Routes messages to NIM, handles tool calls, executes actions via ToolExecutor.
    """

    def __init__(self, user):
        self.user = user
        self.tool_executor = None  # Lazy init

    def _get_tool_executor(self):
        if self.tool_executor is None:
            from .tool_executor import ToolExecutor
            self.tool_executor = ToolExecutor(self.user)
        return self.tool_executor

    async def process_message(
        self,
        content: str,
        agent_type: str = "general",
        conversation_history: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        Process a user message through NIM and handle any tool calls.

        Returns:
            {
                "response": str,
                "agent_type": str,
                "actions_taken": [...],
                "tool_calls": [...],
                "metadata": {...}
            }
        """
        system_prompt = AGENT_SYSTEM_PROMPTS.get(agent_type, AGENT_SYSTEM_PROMPTS["general"])
        messages = [{"role": "system", "content": system_prompt}]

        if conversation_history:
            messages.extend(conversation_history[-10:])  # Last 10 messages

        messages.append({"role": "user", "content": content})

        actions_taken = []
        tool_calls = []
        max_iterations = 5

        for _ in range(max_iterations):
            nim_response = await self._call_nim(messages)
            if not nim_response:
                return {
                    "response": "I'm having trouble processing your request. Please try again.",
                    "agent_type": agent_type,
                    "actions_taken": [],
                    "tool_calls": [],
                    "metadata": {"error": "nim_unavailable"},
                }

            choice = nim_response["choices"][0]
            message = choice["message"]

            # Add assistant message to history
            messages.append(message)

            # Check for tool calls
            if message.get("tool_calls"):
                for tc in message["tool_calls"]:
                    func = tc["function"]
                    tool_name = func["name"]
                    try:
                        args = json.loads(func["arguments"])
                    except json.JSONDecodeError:
                        args = {}

                    # Execute the tool
                    executor = self._get_tool_executor()
                    result = await executor.execute(tool_name, args)
                    tool_calls.append({"tool": tool_name, "args": args, "result": result})
                    actions_taken.append({"action": tool_name, "status": "success" if result.get("success") else "error"})

                    # Feed result back to NIM
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": json.dumps(result),
                    })
            else:
                # No more tool calls — return the text response
                return {
                    "response": message.get("content", ""),
                    "agent_type": agent_type,
                    "actions_taken": actions_taken,
                    "tool_calls": tool_calls,
                    "metadata": {
                        "model": NIM_MODEL,
                        "finish_reason": choice.get("finish_reason"),
                        "iterations": len(actions_taken),
                    },
                }

        # Exhausted max iterations
        return {
            "response": "I've completed the requested actions.",
            "agent_type": agent_type,
            "actions_taken": actions_taken,
            "tool_calls": tool_calls,
            "metadata": {"iterations": max_iterations, "max_reached": True},
        }

    async def _call_nim(self, messages: List[Dict]) -> Optional[Dict]:
        """Call NVIDIA NIM API."""
        if not NIM_API_KEY:
            logger.warning("NIM_API_KEY not set — using fallback response")
            return {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": "AI services are not configured. Please set the NIM_API_KEY.",
                    },
                    "finish_reason": "stop",
                }]
            }

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{NIM_BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {NIM_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": NIM_MODEL,
                        "messages": messages,
                        "tools": AVAILABLE_TOOLS,
                        "tool_choice": "auto",
                        "temperature": 0.3,
                        "max_tokens": 2048,
                    },
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error(f"NIM API error: {e}")
            return None


# ─── Conversation memory ─────────────────────────────────────────────

class ConversationStore:
    """Simple in-memory conversation store per user."""

    _store: Dict[str, List[Dict]] = {}

    @classmethod
    def get_history(cls, user_id: str, agent_type: str = "general") -> List[Dict]:
        key = f"{user_id}:{agent_type}"
        return cls._store.get(key, [])

    @classmethod
    def add_message(cls, user_id: str, agent_type: str, role: str, content: str):
        key = f"{user_id}:{agent_type}"
        if key not in cls._store:
            cls._store[key] = []
        cls._store[key].append({"role": role, "content": content})
        # Keep last 20 messages
        cls._store[key] = cls._store[key][-20:]

    @classmethod
    def clear(cls, user_id: str, agent_type: str = "general"):
        key = f"{user_id}:{agent_type}"
        cls._store.pop(key, None)
