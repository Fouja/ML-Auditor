"""
Tests for the LangGraph agent loop (offline, using a stub chat model).
"""

import pytest
from langchain_core.messages import AIMessage
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

from apps.agents.services.agent_command import AgentCommandService
from apps.agents.services.agent_graph import run_agent

pytestmark = pytest.mark.django_db


def _patch_tool_sync_to_async():
    """Mock sync_to_async so tools avoid real DB writes from worker threads."""
    mock_task = MagicMock()
    mock_task.id = "test-uuid-123"
    mock_task.title = "Graph Task"
    stack = ExitStack()
    mock_sync = stack.enter_context(
        patch("apps.agents.services.tool_executor.sync_to_async")
    )
    mock_sync.return_value = AsyncMock(return_value=mock_task)
    return stack


class StubChatModel:
    """Stand-in for ChatOpenAI that returns scripted AIMessages."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.model_name = "stub-model"
        self.calls = []

    def bind_tools(self, tools):
        self.tools = tools
        return self

    async def ainvoke(self, messages):
        self.calls.append(messages)
        return self.responses.pop(0)


def _tool_call(name, args, call_id):
    return AIMessage(
        content="",
        tool_calls=[
            {"name": name, "args": args, "id": call_id, "type": "tool_call"}
        ],
    )


@pytest.mark.asyncio
class TestAgentGraph:
    async def test_direct_answer_without_tools(self, user):
        service = AgentCommandService(user)
        result = await run_agent(
            service, "What is 2+2?", model=StubChatModel([AIMessage(content="4")])
        )
        assert result["response"] == "4"
        assert result["actions_taken"] == []
        assert result["tool_calls"] == []

    async def test_tool_execution_via_graph(self, user):
        service = AgentCommandService(user)
        model = StubChatModel(
            [
                _tool_call("list_tasks", {}, "call_1"),
                AIMessage(content="Here are your tasks."),
            ]
        )
        with _patch_tool_sync_to_async():
            result = await run_agent(
                service, "What do I have to do?", model=model
            )
        assert result["response"] == "Here are your tasks."
        assert result["actions_taken"] == [
            {"action": "list_tasks", "status": "success"}
        ]
        assert result["tool_calls"][0]["tool"] == "list_tasks"

    async def test_write_tool_pending_confirmation_via_graph(self, user):
        service = AgentCommandService(user)
        model = StubChatModel(
            [
                _tool_call("create_task", {"title": "Graph Task"}, "call_1"),
                AIMessage(content="I'll create that task once you confirm."),
            ]
        )
        with _patch_tool_sync_to_async():
            result = await run_agent(
                service, "Please create a task called Graph Task", model=model
            )
        assert result["response"] == "I'll create that task once you confirm."
        assert result["actions_taken"] == [
            {"action": "create_task", "status": "pending", "args": {"title": "Graph Task"}}
        ]
        assert result["pending_actions"] == [
            {"tool": "create_task", "args": {"title": "Graph Task"}}
        ]
        assert result["tool_calls"][0]["tool"] == "create_task"

    async def test_unknown_tool_reports_error(self, user):
        service = AgentCommandService(user)
        model = StubChatModel(
            [
                _tool_call("nonexistent_tool", {}, "call_2"),
                AIMessage(content="That tool is not available."),
            ]
        )
        result = await run_agent(service, "run unknown tool", model=model)
        assert result["response"] == "That tool is not available."
        assert result["actions_taken"][0]["status"] == "error"

    async def test_uses_conversation_history(self, user):
        service = AgentCommandService(user)
        model = StubChatModel([AIMessage(content="Hey again!")])
        result = await run_agent(
            service,
            "Hello",
            conversation_history=[
                {"role": "user", "content": "Hi"},
                {"role": "assistant", "content": "Hi there"},
            ],
            model=model,
        )
        assert result["response"] == "Hey again!"
        assert len(model.calls[0]) >= 4

    async def test_max_iterations_bound(self, user):
        service = AgentCommandService(user)
        scripted = [
            _tool_call("create_task", {"title": f"Task {i}"}, f"call-{i}")
            for i in range(6)
        ]
        with _patch_tool_sync_to_async():
            result = await run_agent(service, "loop", model=StubChatModel(scripted))
        assert result["response"] == "I've completed the requested actions."
        assert len(result["actions_taken"]) == 5
        assert result["metadata"]["iterations"] == 5

    async def test_canned_response_when_no_api_key(self, user):
        service = AgentCommandService(user)
        result = await run_agent(service, "hello")
        assert "AI services are not configured" in result["response"]
        assert result["metadata"]["error"] == "llm_not_configured"
        assert result["actions_taken"] == []

    async def test_file_url_surfaced_in_metadata(self, user, settings):
        from unittest.mock import patch

        service = AgentCommandService(user)
        model = StubChatModel(
            [
                _tool_call("get_bank_statement_pdf", {"month": 5, "year": 2026}, "call_x"),
                AIMessage(content="Statement ready!"),
            ]
        )

        with patch(
            "apps.agents.services.bank_statement_pdf.generate_bank_statement_pdf",
            return_value={
                "success": True,
                "file_url": "/media/bank_statements/1/bank-statement-2026-05.pdf",
            },
        ) as mock_gen:
            result = await run_agent(service, "Get my May statement", model=model)

        assert result["metadata"]["file_url"] == (
            "/media/bank_statements/1/bank-statement-2026-05.pdf"
        )
        mock_gen.assert_called_once()
