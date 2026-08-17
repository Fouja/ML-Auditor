"""
LangGraph agent — orchestrates the assistant loop.

Replaces the hand-rolled NIM loop with a LangGraph state machine:

    retrieve_context -> call_model -> execute_tools -> call_model -> ... -> end

The graph reuses the existing ToolExecutor and RAG helpers on
AgentCommandService, and the model is injectable so tests can run
offline with a stub chat model.
"""

import asyncio
import json
import logging
from typing import Annotated, Any, Dict, List, Optional, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import START, END, StateGraph, add_messages

from .agent_command import (
    AGENT_SYSTEM_PROMPTS,
    AVAILABLE_TOOLS,
    CREATIVITY_PROMPTS,
    NIM_MODEL,
    WEB_TOOLS,
    WRITE_TOOLS,
)

logger = logging.getLogger(__name__)

METRICS_LOGGER = logging.getLogger("apps.metrics")


def _log_metric(event: str, data: Dict[str, Any]) -> None:
    """Emit a structured metric that the JSON formatter ships to Elasticsearch."""
    METRICS_LOGGER.info(event, extra={"metrics": data})


def _user_id(state: Dict[str, Any]) -> str:
    user = state.get("user")
    return str(getattr(user, "id", "")) if user else ""

MAX_ITERATIONS = 5

# Hard per-step deadlines. NIM can return 504s and Kijiji-style scrapes can
# stall, so every network/blocking step is bounded to keep the request from
# hanging for minutes.
MODEL_TIMEOUT = 90
TOOL_TIMEOUT = 30
RAG_TIMEOUT = 20
GLOBAL_TIMEOUT = 180


class AgentState(TypedDict):
    user: Any
    agent_type: str
    messages: Annotated[list, add_messages]
    actions_taken: List[Dict[str, Any]]
    tool_calls: List[Dict[str, Any]]
    pending_actions: List[Dict[str, Any]]
    rag_context: Optional[str]
    iterations: int
    max_iterations: int
    api_key_configured: bool
    model_name: str
    temperature: float
    max_tokens: int
    creativity_level: str
    context_depth: int
    web_tools_enabled: bool
    rag_max_chunks: int


def _clamp_int(value: Any, default: int, lo: int = 0, hi: int = 100) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, n))


def _resolve_studio(settings: Optional[Dict[str, Any]], user: Any) -> Dict[str, Any]:
    settings = settings or {}
    creativity = _clamp_int(settings.get("creativity"), 50)
    context_depth = _clamp_int(settings.get("context_depth"), 55)
    token_budget = _clamp_int(settings.get("token_budget"), 70)
    level = (settings.get("creativity_level") or "").lower()
    if level not in CREATIVITY_PROMPTS:
        if creativity <= 33:
            level = "low"
        elif creativity <= 66:
            level = "normal"
        else:
            level = "high"
    temp_map = {"low": 0.2, "normal": 0.5, "high": 0.9}
    temperature = temp_map[level]
    max_tokens = int(256 + (token_budget / 100) * (4096 - 256))
    rag_max_chunks = int(2 + (context_depth / 100) * 13)
    web_tools_enabled = bool(getattr(user, "web_tools_enabled", False))
    return {
        "temperature": temperature,
        "max_tokens": max_tokens,
        "creativity_level": level,
        "context_depth": context_depth,
        "web_tools_enabled": web_tools_enabled,
        "rag_max_chunks": rag_max_chunks,
    }


def _tools_for_user(web_tools_enabled: bool) -> List[Dict[str, Any]]:
    if web_tools_enabled:
        return AVAILABLE_TOOLS
    return [
        t
        for t in AVAILABLE_TOOLS
        if t.get("function", {}).get("name") not in WEB_TOOLS
    ]


def _extract_sources(tool_calls: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    sources: List[Dict[str, str]] = []
    seen = set()
    for call in tool_calls:
        tool = call.get("tool") or ""
        result = call.get("result") or {}
        if not result.get("success"):
            continue
        if tool == "web_search":
            for item in result.get("results") or []:
                url = item.get("url") or item.get("link") or ""
                if not url or url in seen:
                    continue
                seen.add(url)
                sources.append(
                    {
                        "title": item.get("title") or item.get("name") or url,
                        "url": url,
                    }
                )
        elif tool == "fetch_webpage":
            url = result.get("url") or (call.get("args") or {}).get("url") or ""
            if url and url not in seen:
                seen.add(url)
                sources.append({"title": url, "url": url})
        elif tool == "get_recent_news":
            for article in result.get("articles") or []:
                url = article.get("url") or ""
                if not url or url in seen:
                    continue
                seen.add(url)
                sources.append(
                    {
                        "title": article.get("title") or url,
                        "url": url,
                    }
                )
    return sources


def _extract_rag_query(messages: list) -> str:
    """Use the most recent user message as the RAG query."""
    for msg in reversed(messages):
        if getattr(msg, "type", None) == "human":
            return getattr(msg, "content", "") or ""
    return ""


def _as_message(msg: Dict[str, Any]) -> Any:
    role = msg.get("role")
    content = msg.get("content", "")
    if role == "assistant":
        return AIMessage(content=content)
    return HumanMessage(content=content)


def build_agent_graph(service, model=None):
    """Build a compiled LangGraph for a given AgentCommandService.

    Args:
        service: AgentCommandService instance (holds user + RAG/config helpers).
        model: Optional chat model to use instead of a real NIM-backed
            ChatOpenAI instance. Used for offline tests.
    """
    async def retrieve_context(state: AgentState) -> Dict[str, Any]:
        if state.get("rag_context"):
            return {"rag_context": state["rag_context"]}
        query = _extract_rag_query(state["messages"])
        if query:
            try:
                max_chunks = int(state.get("rag_max_chunks") or 5)
                ctx = await asyncio.wait_for(
                    service._retrieve_rag_context(query, max_chunks=max_chunks),
                    timeout=RAG_TIMEOUT,
                )
                return {"rag_context": ctx or ""}
            except asyncio.TimeoutError:
                logger.warning(f"RAG context retrieval timed out after {RAG_TIMEOUT}s")
            except Exception as e:
                logger.warning(f"RAG context retrieval failed in graph: {e}")
        return {"rag_context": ""}

    async def call_model(state: AgentState) -> Dict[str, Any]:
        import time as _time

        model_name = NIM_MODEL
        temperature = float(state.get("temperature") or 0.5)
        max_tokens = int(state.get("max_tokens") or 2048)
        if model is None:
            api_key, base_url, model_name, provider = await service._get_nim_config()
            if not api_key and provider not in {"ollama", "lmstudio"}:
                logger.warning("No LLM API key found — using canned response")
                return {
                    "messages": [
                        AIMessage(
                            content="AI services are not configured. Please set the NIM_API_KEY or an active LLM configuration."
                        )
                    ],
                    "api_key_configured": False,
                    "model_name": model_name,
                }
            if provider == "anthropic":
                from langchain_anthropic import ChatAnthropic

                llm = ChatAnthropic(
                    model=model_name,
                    api_key=api_key or "not-needed",
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=MODEL_TIMEOUT,
                    max_retries=1,
                )
            else:
                # Keyless local endpoints (Ollama / LM Studio) accept any value.
                llm = ChatOpenAI(
                    model=model_name,
                    api_key=api_key or "local-not-needed",
                    base_url=base_url,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=MODEL_TIMEOUT,
                    max_retries=1,
                )
        else:
            llm = model
            model_name = getattr(model, "model_name", "fake-model")

        system_prompt = AGENT_SYSTEM_PROMPTS.get(
            state["agent_type"], AGENT_SYSTEM_PROMPTS["general"]
        )
        level = state.get("creativity_level") or "normal"
        system_prompt += f"\n\n{CREATIVITY_PROMPTS.get(level, CREATIVITY_PROMPTS['normal'])}"
        if not state.get("web_tools_enabled", False):
            system_prompt += (
                "\n\nWeb tools (web_search, fetch_webpage, get_recent_news) are DISABLED. "
                "If the user asks for live/current information, tell them to activate "
                "Web Tools under Integrations → Web Tools."
            )
        if state.get("rag_context"):
            system_prompt += (
                "\n\nHere is relevant context from your connected data sources "
                "(emails, Jira issues, notes, etc.):\n"
                f"{state['rag_context']}\n\n"
                "Use this context to answer the user's question when relevant."
            )

        try:
            from .feedback_service import build_feedback_prompt

            feedback_prompt = await asyncio.wait_for(
                asyncio.to_thread(
                    build_feedback_prompt, str(getattr(service.user, "id", ""))
                ),
                timeout=5,
            )
            if feedback_prompt:
                system_prompt += f"\n\n{feedback_prompt}"
        except Exception as e:
            logger.debug(f"Feedback prompt injection failed: {e}")

        bound = llm.bind_tools(_tools_for_user(bool(state.get("web_tools_enabled"))))
        messages = [SystemMessage(content=system_prompt), *state["messages"]]
        _start = _time.monotonic()
        try:
            resp = await asyncio.wait_for(bound.ainvoke(messages), timeout=MODEL_TIMEOUT)
            _latency_ms = round((_time.monotonic() - _start) * 1000)
            usage = getattr(resp, "usage_metadata", None) or {}
            _log_metric("llm_call", {
                "metric": "llm_call",
                "metric_type": "llm",
                "model": model_name,
                "agent_type": state["agent_type"],
                "user_id": _user_id(state),
                "latency_ms": _latency_ms,
                "status": "success",
                "prompt_tokens": usage.get("input_tokens") or 0,
                "completion_tokens": usage.get("output_tokens") or 0,
                "total_tokens": usage.get("total_tokens") or 0,
                "tool_calls": len(getattr(resp, "tool_calls", []) or []),
            })
        except asyncio.TimeoutError:
            _latency_ms = round((_time.monotonic() - _start) * 1000)
            logger.error(f"Model call timed out after {MODEL_TIMEOUT}s")
            _log_metric("llm_call_timeout", {
                "metric": "llm_call",
                "metric_type": "llm",
                "model": model_name,
                "agent_type": state["agent_type"],
                "user_id": _user_id(state),
                "latency_ms": _latency_ms,
                "status": "timeout",
                "error": "timeout",
            })
            return {
                "messages": [
                    AIMessage(
                        content=(
                            "I'm sorry, the AI service took too long to respond. "
                            "Please try again."
                        )
                    )
                ],
                "api_key_configured": True,
                "model_name": model_name,
            }
        except Exception as e:
            _latency_ms = round((_time.monotonic() - _start) * 1000)
            logger.error(f"Model call failed: {e}")
            _log_metric("llm_call_error", {
                "metric": "llm_call",
                "metric_type": "llm",
                "model": model_name,
                "agent_type": state["agent_type"],
                "user_id": _user_id(state),
                "latency_ms": _latency_ms,
                "status": "error",
                "error": str(e)[:300],
            })
            raise
        if isinstance(resp, str):
            resp = AIMessage(content=resp)
        usage = getattr(resp, "usage_metadata", None) or {}
        return {
            "messages": [resp],
            "api_key_configured": True,
            "model_name": model_name,
            "_completion_tokens": int(usage.get("output_tokens") or 0),
        }

    async def execute_tools(state: AgentState) -> Dict[str, Any]:
        import time as _time

        last = state["messages"][-1]
        tool_calls = getattr(last, "tool_calls", []) or []
        executor = service._get_tool_executor()
        tool_messages: List[Any] = []
        actions: List[Dict[str, Any]] = []
        calls: List[Dict[str, Any]] = []
        pending: List[Dict[str, Any]] = []
        for tc in tool_calls:
            tool_name = tc.get("name", "")
            args = tc.get("args") or {}
            _t_start = _time.monotonic()
            if tool_name in WRITE_TOOLS:
                # Write tools are only proposed — the user must confirm before
                # they run. Record the proposal and let the model summarize it.
                pending.append({"tool": tool_name, "args": args})
                actions.append(
                    {
                        "action": tool_name,
                        "status": "pending",
                        "args": args,
                    }
                )
                calls.append(
                    {
                        "tool": tool_name,
                        "args": args,
                        "result": {
                            "success": True,
                            "pending_confirmation": True,
                        },
                    }
                )
                _log_metric("tool_call", {
                    "metric": "tool_call",
                    "metric_type": "agent",
                    "tool": tool_name,
                    "user_id": _user_id(state),
                    "agent_type": state["agent_type"],
                    "status": "pending",
                    "latency_ms": 0,
                })
                tool_messages.append(
                    ToolMessage(
                        content=json.dumps(
                            {
                                "pending_confirmation": True,
                                "message": f"{tool_name} is awaiting the user's confirmation.",
                            }
                        ),
                        tool_call_id=tc.get("id", ""),
                    )
                )
                continue
            try:
                result = await asyncio.wait_for(
                    executor.execute(tool_name, args), timeout=TOOL_TIMEOUT
                )
                _t_ms = round((_time.monotonic() - _t_start) * 1000)
                _log_metric("tool_call", {
                    "metric": "tool_call",
                    "metric_type": "agent",
                    "tool": tool_name,
                    "user_id": _user_id(state),
                    "agent_type": state["agent_type"],
                    "status": "success" if result.get("success") else "error",
                    "latency_ms": _t_ms,
                })
            except asyncio.TimeoutError:
                _t_ms = round((_time.monotonic() - _t_start) * 1000)
                logger.error(f"Tool {tool_name} timed out after {TOOL_TIMEOUT}s")
                _log_metric("tool_call_timeout", {
                    "metric": "tool_call",
                    "metric_type": "agent",
                    "tool": tool_name,
                    "user_id": _user_id(state),
                    "agent_type": state["agent_type"],
                    "status": "timeout",
                    "latency_ms": _t_ms,
                })
                result = {
                    "success": False,
                    "error": f"Tool {tool_name} timed out. Try rephrasing your request.",
                }
            except Exception as e:
                _t_ms = round((_time.monotonic() - _t_start) * 1000)
                logger.error(f"Tool {tool_name} failed: {e}")
                _log_metric("tool_call_error", {
                    "metric": "tool_call",
                    "metric_type": "agent",
                    "tool": tool_name,
                    "user_id": _user_id(state),
                    "agent_type": state["agent_type"],
                    "status": "error",
                    "latency_ms": _t_ms,
                    "error": str(e)[:300],
                })
                result = {"success": False, "error": str(e)}
            tool_messages.append(
                ToolMessage(
                    content=json.dumps(result),
                    tool_call_id=tc.get("id", ""),
                )
            )
            actions.append(
                {
                    "action": tool_name,
                    "status": "success" if result.get("success") else "error",
                }
            )
            calls.append({"tool": tool_name, "args": args, "result": result})
        return {
            "messages": tool_messages,
            "actions_taken": state["actions_taken"] + actions,
            "tool_calls": state["tool_calls"] + calls,
            "pending_actions": state["pending_actions"] + pending,
            "iterations": state["iterations"] + 1,
        }

    def should_continue(state: AgentState) -> str:
        last = state["messages"][-1]
        has_tool_calls = bool(getattr(last, "tool_calls", []))
        if has_tool_calls and state["iterations"] < state["max_iterations"]:
            return "tools"
        return "end"

    graph = StateGraph(AgentState)
    graph.add_node("retrieve_context", retrieve_context)
    graph.add_node("call_model", call_model)
    graph.add_node("execute_tools", execute_tools)
    graph.add_edge(START, "retrieve_context")
    graph.add_edge("retrieve_context", "call_model")
    graph.add_conditional_edges(
        "call_model", should_continue, {"tools": "execute_tools", "end": END}
    )
    graph.add_edge("execute_tools", "call_model")
    return graph.compile()


async def run_agent(
    service,
    content: str,
    agent_type: str = "general",
    conversation_history: Optional[List[Dict[str, Any]]] = None,
    model=None,
    studio_settings: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run the LangGraph agent and return the response contract.

    Returns:
        {
            "response": str,
            "agent_type": str,
            "actions_taken": [...],
            "tool_calls": [...],
            "metadata": {...}
        }
    """
    history = conversation_history or []
    initial_messages = [_as_message(m) for m in history[-10:]]
    initial_messages.append(HumanMessage(content=content))
    studio = _resolve_studio(studio_settings, service.user)

    import time as _time
    _start = _time.monotonic()
    graph = build_agent_graph(service, model=model)
    try:
        result = await asyncio.wait_for(
            graph.ainvoke(
                {
                    "user": service.user,
                    "agent_type": agent_type,
                    "messages": initial_messages,
                    "actions_taken": [],
                    "tool_calls": [],
                    "pending_actions": [],
                    "rag_context": None,
                    "iterations": 0,
                    "max_iterations": MAX_ITERATIONS,
                    "api_key_configured": True,
                    "model_name": NIM_MODEL,
                    **studio,
                }
            ),
            timeout=GLOBAL_TIMEOUT,
        )
        _total_ms = round((_time.monotonic() - _start) * 1000)
        _log_metric("agent_run", {
            "metric": "agent_run",
            "metric_type": "agent",
            "user_id": str(getattr(service.user, "id", "")),
            "agent_type": agent_type,
            "status": "success",
            "latency_ms": _total_ms,
            "iterations": result.get("iterations", 0),
            "tool_calls_count": len(result.get("tool_calls", [])),
            "pending_actions_count": len(result.get("pending_actions", [])),
            "model": result.get("model_name", NIM_MODEL),
        })
    except asyncio.TimeoutError:
        _total_ms = round((_time.monotonic() - _start) * 1000)
        logger.error(f"Agent run timed out after {GLOBAL_TIMEOUT}s")
        _log_metric("agent_run_timeout", {
            "metric": "agent_run",
            "metric_type": "agent",
            "user_id": str(getattr(service.user, "id", "")),
            "agent_type": agent_type,
            "status": "timeout",
            "latency_ms": _total_ms,
            "iterations": 0,
        })
        return {
            "response": (
                "The request took too long to complete. "
                "Please try again or rephrase your request."
            ),
            "agent_type": agent_type,
            "actions_taken": [],
            "tool_calls": [],
            "pending_actions": [],
            "metadata": {
                "model": NIM_MODEL,
                "error": "timeout",
                "iterations": 0,
                "max_iterations": MAX_ITERATIONS,
            },
        }

    response = ""
    for msg in reversed(result.get("messages", [])):
        if getattr(msg, "type", None) == "ai":
            response = getattr(msg, "content", "") or ""
            break
    if not response:
        response = "I've completed the requested actions."

    actions_taken = result.get("actions_taken", [])
    tool_calls = result.get("tool_calls", [])
    pending_actions = result.get("pending_actions", [])

    metadata: Dict[str, Any] = {
        "model": result.get("model_name", NIM_MODEL),
        "iterations": result.get("iterations", 0),
        "max_iterations": MAX_ITERATIONS,
        "creativity_level": studio.get("creativity_level"),
        "web_tools_enabled": studio.get("web_tools_enabled"),
        "latency_ms": _total_ms,
        "completion_tokens": int(result.get("_completion_tokens", 0) or 0),
    }
    if pending_actions:
        metadata["pending_actions"] = pending_actions
    if not result.get("api_key_configured", True):
        metadata["error"] = "llm_not_configured"

    file_urls = [
        call.get("result", {}).get("file_url")
        for call in tool_calls
        if call.get("result", {}).get("file_url")
    ]
    if file_urls:
        metadata["file_url"] = file_urls[0]
        metadata["file_urls"] = file_urls

    sources = _extract_sources(tool_calls)
    if sources:
        metadata["sources"] = sources

    return {
        "response": response,
        "agent_type": agent_type,
        "actions_taken": actions_taken,
        "tool_calls": tool_calls,
        "pending_actions": pending_actions,
        "metadata": metadata,
    }
