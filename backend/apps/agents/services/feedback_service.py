"""
Human feedback service — stores user ratings/comments in Elasticsearch and
surfaces "lessons" that the agent injects into its context so it can learn
from past feedback without retraining.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

ES_URL = getattr(settings, "ELASTICSEARCH_URL", "http://localhost:9200")
INDEX_PREFIX = "ml-auditor-feedback"

POSITIVE_THRESHOLD = 4
NEGATIVE_THRESHOLD = 2


def _index_for_today() -> str:
    return f"{INDEX_PREFIX}-{datetime.utcnow().strftime('%Y.%m.%d')}"


def submit_feedback(
    user_id: str,
    rating: int,
    comment: str = "",
    agent_type: str = "general",
    user_message: str = "",
    agent_response: str = "",
    tool_calls: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Persist a feedback record to Elasticsearch."""
    doc = {
        "@timestamp": datetime.utcnow().isoformat() + "Z",
        "user_id": user_id,
        "rating": int(rating),
        "comment": comment,
        "agent_type": agent_type,
        "user_message": user_message[:2000],
        "agent_response": agent_response[:4000],
        "tool_calls": tool_calls or [],
        "sentiment": _classify(rating),
    }
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.post(
                f"{ES_URL}/{_index_for_today()}/_doc",
                json=doc,
            )
            resp.raise_for_status()
            doc["id"] = resp.json().get("_id")
            return doc
    except Exception as e:
        logger.error(f"Feedback write to ES failed: {e}")
        return {"error": str(e)}


def _classify(rating: int) -> str:
    if rating >= POSITIVE_THRESHOLD:
        return "positive"
    if rating <= NEGATIVE_THRESHOLD:
        return "negative"
    return "neutral"


def get_preferences(user_id: str, limit: int = 8) -> Dict[str, Any]:
    """Retrieve recent feedback for a user and derive learning signals.

    Returns:
        {
            "lessons": [str, ...],      # derived from negative feedback
            "positive_examples": [...], # top-rated exchanges for few-shot
            "total_feedback": int,
        }
    """
    try:
        from django.core.cache import cache

        cached = cache.get(f"feedback_prefs_{user_id}")
        if cached:
            return cached
    except Exception:
        pass

    lessons: List[str] = []
    positive_examples: List[Dict[str, Any]] = []
    total = 0
    try:
        query = {
            "size": limit,
            "sort": [{"@timestamp": "desc"}],
            "query": {"bool": {"must": [{"term": {"user_id.keyword": user_id}}]}},
        }
        with httpx.Client(timeout=10) as client:
            resp = client.post(
                f"{ES_URL}/{INDEX_PREFIX}-*/_search",
                json=query,
            )
            resp.raise_for_status()
            hits = resp.json().get("hits", {}).get("hits", [])
            total = resp.json().get("hits", {}).get("total", {}).get("value", len(hits))
        for hit in hits:
            src = hit.get("_source", {})
            rating = int(src.get("rating", 0))
            if rating <= NEGATIVE_THRESHOLD:
                comment = (src.get("comment") or "").strip()
                response = (src.get("agent_response") or "").strip()
                detail = comment or (f"Response: {response[:200]}" if response else "")
                if detail:
                    lessons.append(
                        f"The user rated a past answer poorly ({rating}/5). "
                        f"What they said: {detail}"
                    )
            elif rating >= POSITIVE_THRESHOLD and (src.get("user_message") or src.get("agent_response")):
                positive_examples.append(
                    {
                        "user_message": (src.get("user_message") or "")[:400],
                        "agent_response": (src.get("agent_response") or "")[:400],
                    }
                )
    except Exception as e:
        logger.warning(f"Feedback preference retrieval failed: {e}")

    result = {
        "lessons": lessons,
        "positive_examples": positive_examples,
        "total_feedback": total,
    }
    try:
        cache.set(f"feedback_prefs_{user_id}", result, timeout=60)
    except Exception:
        pass
    return result


def build_feedback_prompt(user_id: str) -> str:
    """Build a short context block for the system prompt from past feedback."""
    prefs = get_preferences(user_id)
    parts: List[str] = []
    if prefs.get("lessons"):
        parts.append("Feedback you should keep in mind from this user's past ratings:")
        parts.extend(f"- {lesson}" for lesson in prefs["lessons"])
    if prefs.get("positive_examples"):
        parts.append("Past exchanges the user liked (use them as a style guide):")
        for ex in prefs["positive_examples"]:
            parts.append(
                f"- User: {ex['user_message']} | Assistant: {ex['agent_response']}"
            )
    return "\n".join(parts)
