"""
Agent command service — orchestrates agents via NIM.
Routes user messages to the right agent, handles tool calls, and returns structured responses.
The orchestration loop is implemented with LangGraph (see services/agent_graph.py).
"""

import logging
from typing import Any, Dict, List, Optional

from django.conf import settings

logger = logging.getLogger(__name__)

NIM_BASE_URL = getattr(settings, "NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
NIM_MODEL = getattr(settings, "NIM_MODEL", "meta/llama-3.1-8b-instruct")
NIM_API_KEY = getattr(settings, "NIM_API_KEY", "")


# ─── Agent definitions ───────────────────────────────────────────────

WEB_TOOLS = frozenset({"web_search", "fetch_webpage", "get_recent_news"})

CREATIVITY_PROMPTS = {
    "low": (
        "Creativity mode: LOW. Prefer precise, factual, concise answers. "
        "Avoid speculation, flourish, or creative embellishment."
    ),
    "normal": (
        "Creativity mode: NORMAL. Balance accuracy with helpful, natural wording."
    ),
    "high": (
        "Creativity mode: HIGH. Be exploratory and imaginative while remaining useful. "
        "Offer alternative angles and creative suggestions when appropriate."
    ),
}

AGENT_SYSTEM_PROMPTS = {
    "general": (
        "You are Argus, a watchful and helpful AI assistant. "
        "You see everything the user connects — emails, calendar, bank transactions, "
        "notes, news — and you answer from that grounded context first. "
        "RULES FOR TOOL USE:\n"
        "1. For casual chat, greetings, small talk, or questions that don't require "
        "your tools, reply directly with a normal answer. Do NOT call any tool.\n"
        "2. Only use a tool when the user EXPLICITLY asks you to perform an action "
        "(e.g. 'create a task', 'send an email', 'search for X', 'analyze my spending').\n"
        "3. For questions about the user's own data (emails, jobs, transactions, "
        "calendar, notes), rely on the synced context provided below ('relevant "
        "context from your connected data sources') rather than guessing. If the "
        "synced context is empty, tell the user to connect and sync that source.\n"
        "4. Never call 'send_email' unless the user gave you a real recipient email "
        "address and explicitly asked to send it. Never invent recipients, addresses, "
        "subjects, amounts, or other data. If information is missing, ask the user for it.\n"
        "5. When you need a tool that modifies data (create/update/send), you may "
        "propose it, but the system will ask the user to confirm before it runs.\n"
        "6. Always answer the user in the same language they write in.\n"
        "7. For questions about current events, live information, prices, or things that "
        "may have changed, use 'web_search' (and 'fetch_webpage' to read a specific link) "
        "when those tools are available. Do not guess or rely on stale knowledge.\n"
        "8. When the user asks what is going on today / news / actualites, use "
        "'get_recent_news' to pull from their saved sources, then 'web_search' to "
        "complement with live results. If you are not sure what they want, briefly ask "
        "which topics or sources they care about.\n"
        "9. When the user asks about their tasks, to-do list, Wall of Work, or what "
        "they have to do, use 'list_tasks' to retrieve the current tasks and summarize "
        "them by status and priority. Do not invent tasks.\n"
        "10. When web tools are disabled and the user asks for live/current information, "
        "tell them clearly that Web Tools are not activated and they should enable them "
        "under Integrations → Web Tools. Do not invent live facts."
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
            "name": "create_note",
            "description": "Create a new note",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Note title"},
                    "content": {"type": "string", "description": "Note content"},
                    "format": {
                        "type": "string",
                        "enum": ["note", "book_chapter", "presentation", "article"],
                        "description": "Format of the note",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags for the note",
                    },
                },
                "required": ["title", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_notes",
            "description": "List or search notes",
            "parameters": {
                "type": "object",
                "properties": {
                    "format": {
                        "type": "string",
                        "enum": ["note", "book_chapter", "presentation", "article"],
                        "description": "Filter by format",
                    },
                    "tag": {"type": "string", "description": "Filter by tag"},
                    "query": {"type": "string", "description": "Search in title and content"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_note",
            "description": "Update an existing note",
            "parameters": {
                "type": "object",
                "properties": {
                    "note_id": {"type": "string", "description": "ID of the note to update"},
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                    "format": {
                        "type": "string",
                        "enum": ["note", "book_chapter", "presentation", "article"],
                    },
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["note_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "organize_notes",
            "description": "Organize multiple notes into a structured format (book chapter, presentation, article)",
            "parameters": {
                "type": "object",
                "properties": {
                    "note_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "IDs of notes to organize",
                    },
                    "target_format": {
                        "type": "string",
                        "enum": ["book_chapter", "presentation", "article"],
                        "description": "Target output format",
                    },
                    "style": {
                        "type": "string",
                        "enum": ["professional", "creative", "academic", "simple"],
                        "description": "Writing style",
                    },
                    "title": {"type": "string", "description": "Title for the output"},
                },
                "required": ["note_ids", "target_format"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_tasks",
            "description": (
                "List the user's tasks from the Wall of Work board. Use this when the user asks "
                "about their to-do list, what they have to do, their tasks, or the Wall of Work. "
                "Returns task title, status, priority, due date, description, and tags."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["todo", "in_progress", "review", "done"],
                        "description": "Optional filter by task status",
                    },
                    "query": {
                        "type": "string",
                        "description": "Optional keyword to search in task title and description",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_task",
            "description": "Create a new task on the Wall of Work board",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Task title"},
                    "status": {
                        "type": "string",
                        "enum": ["todo", "in_progress", "review", "done"],
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "critical"],
                    },
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
                    "days": {
                        "type": "integer",
                        "description": "Number of days to analyze",
                    },
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
                    "tone": {
                        "type": "string",
                        "enum": ["professional", "friendly", "formal", "casual"],
                    },
                },
                "required": ["original_subject", "draft_body"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "jira_get_projects",
            "description": "List Jira projects",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "jira_get_issues",
            "description": "Get issues from a Jira project",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_key": {"type": "string", "description": "Jira project key (e.g. PROJ)"},
                    "jql": {"type": "string", "description": "JQL query string"},
                    "max_results": {"type": "integer", "description": "Max results to return"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "jira_search",
            "description": "Search Jira issues for RAG context",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search text to find matching issues"},
                    "max_results": {"type": "integer"},
                },
                "required": ["query"],
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
    {
        "type": "function",
        "function": {
            "name": "get_bank_statement_pdf",
            "description": "Generate a formal PDF bank statement for a specific month and year from the user's Plaid-connected bank accounts. The statement includes the bank logo and address, account holder info, a summary of deposits/withdrawals, and an itemised transaction list.",
            "parameters": {
                "type": "object",
                "properties": {
                    "month": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 12,
                        "description": "Month number (1-12)",
                    },
                    "year": {
                        "type": "integer",
                        "description": "Year, e.g. 2026",
                    },
                    "account_id": {
                        "type": "string",
                        "description": "Optional Plaid account ID to restrict the statement to a single account",
                    },
                },
                "required": ["month", "year"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Search the live internet for current information, news, prices, facts, "
                "or anything that may have changed recently. Use this for questions about "
                "current events, today's news, or topics you are not confident about. "
                "Returns search results with titles, URLs and snippets."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"},
                    "num_results": {
                        "type": "integer",
                        "description": "Number of results to return (1-10)",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_webpage",
            "description": (
                "Read the content of a specific web page or URL (article, X/Twitter post, "
                "LinkedIn page, blog post, docs, etc.) and return it as clean readable "
                "markdown. Use this when the user gives you a link, or to read a page "
                "found by web_search."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The full http(s) URL to read",
                    }
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_news",
            "description": (
                "Retrieve recently scraped articles from the user's saved news sources "
                "(their 'Actualites' section: RSS feeds and web pages). Use this when the "
                "user asks 'what is going on today', 'any news?', or about their tracked "
                "sources/topics. Optionally filter by a keyword or a source name."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Optional keyword to filter articles by",
                    },
                    "days": {
                        "type": "integer",
                        "description": "How many days back to look (default 1 = today)",
                    },
                },
            },
        },
    },
]


# Tools that modify data — these are proposed to the user and only executed
# after explicit confirmation (never auto-run inside the agent loop).
WRITE_TOOLS = {
    "create_note",
    "update_note",
    "organize_notes",
    "create_task",
    "send_email",
    "create_calendar_event",
    "draft_email_reply",
}


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
        studio_settings: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process a user message through the LangGraph agent and handle any tool calls.

        Returns:
            {
                "response": str,
                "agent_type": str,
                "actions_taken": [...],
                "tool_calls": [...],
                "metadata": {...}
            }
        """
        from .agent_graph import run_agent

        return await run_agent(
            self,
            content=content,
            agent_type=agent_type,
            conversation_history=conversation_history,
            studio_settings=studio_settings,
        )

    async def _retrieve_rag_context(self, query: str, max_chunks: int = 5) -> Optional[str]:
        """Search DocumentChunks for relevant context via the modular RAG pipeline."""
        try:
            from asgiref.sync import sync_to_async

            from apps.document_chunks.services.rag.service import query_rag

            result = await sync_to_async(query_rag)(
                self.user,
                query,
                limit=max_chunks,
                min_score=0.30,
            )
            hits = result.get("results") or []
            if not hits:
                return None

            parts = []
            for hit in hits:
                source = hit.get("category") or "general"
                label = f"[{source}]"
                parts.append(f"{label} {hit['content'][:500]}")
            return "\n\n---\n\n".join(parts)
        except Exception as e:
            logger.warning(f"RAG context retrieval failed: {e}")
            return None

    async def _get_nim_config(self) -> tuple[str, str, str, str]:
        """Get LLM API key, base URL, model and provider, checking env first then DB config.

        Returns a 4-tuple ``(api_key, base_url, model, provider)``. Provider is
        used by the graph to pick the right chat-model client (OpenAI-compatible
        vs Anthropic vs local keyless)."""
        api_key = NIM_API_KEY
        base_url = NIM_BASE_URL
        model = NIM_MODEL
        provider = "nvidia"

        # Prefer user's active LLM config from DB (set via Settings → LLM Configuration)
        if not api_key:
            try:
                from asgiref.sync import sync_to_async

                from apps.integrations.models import LLMConfiguration

                def _load_config():
                    return LLMConfiguration.objects.filter(
                        user=self.user, is_active=True
                    ).first()

                active = await sync_to_async(_load_config)()
                if active:
                    api_key = active.decrypted_api_key
                    if active.api_endpoint:
                        base_url = active.api_endpoint.rstrip("/")
                    if active.model_name:
                        model = active.model_name
                    provider = active.provider
            except Exception as e:
                logger.warning(f"LLM config lookup failed: {e}")
        return api_key, base_url, model, provider


# ─── Conversation memory ─────────────────────────────────────────────


class ConversationStore:
    """Per-user conversation store backed by the database.

    Keeps the same class-method API as the old in-memory store so callers
    (chat endpoint, clear-history endpoint) are unchanged.
    """

    MAX_MESSAGES = 20

    @classmethod
    def _get_or_create_conversation(cls, user, agent_type: str = "general"):
        from apps.agents.models import Conversation

        conversation, _ = Conversation.objects.get_or_create(
            user=user,
            agent_type=agent_type,
            defaults={"title": agent_type},
        )
        return conversation

    @classmethod
    def get_history(cls, user_id: str, agent_type: str = "general") -> List[Dict]:
        from django.contrib.auth import get_user_model
        from apps.agents.models import Conversation

        try:
            user = get_user_model().objects.get(id=user_id)
            conversation = Conversation.objects.filter(
                user=user, agent_type=agent_type
            ).first()
            if not conversation:
                return []
            messages = conversation.messages.all()[: cls.MAX_MESSAGES]
            return [{"role": m.role, "content": m.content} for m in messages]
        except Exception:
            return []

    @classmethod
    def add_message(cls, user_id: str, agent_type: str, role: str, content: str):
        from django.contrib.auth import get_user_model
        from apps.agents.models import Conversation, ConversationMessage

        try:
            user = get_user_model().objects.get(id=user_id)
        except Exception:
            return
        conversation = cls._get_or_create_conversation(user, agent_type)
        ConversationMessage.objects.create(
            conversation=conversation, role=role, content=content
        )
        recent = list(conversation.messages.all())
        if len(recent) > cls.MAX_MESSAGES:
            for message in recent[: len(recent) - cls.MAX_MESSAGES]:
                message.delete()
        conversation.save(update_fields=["updated_at"])

    @classmethod
    def clear(cls, user_id: str, agent_type: str = "general"):
        from django.contrib.auth import get_user_model
        from apps.agents.models import Conversation

        try:
            user = get_user_model().objects.get(id=user_id)
            Conversation.objects.filter(user=user, agent_type=agent_type).delete()
        except Exception:
            pass

    @classmethod
    def list_conversations(cls, user, limit: int = 50):
        from apps.agents.models import Conversation

        conversations = (
            Conversation.objects.filter(user=user).select_related("user")[:limit]
        )
        result = []
        for conv in conversations:
            messages = list(conv.messages.all()[: cls.MAX_MESSAGES])
            result.append(
                {
                    "agent_type": conv.agent_type,
                    "title": conv.title or conv.agent_type,
                    "created_at": conv.created_at.isoformat(),
                    "updated_at": conv.updated_at.isoformat(),
                    "messages": [
                        {"role": m.role, "content": m.content} for m in messages
                    ],
                }
            )
        return result
