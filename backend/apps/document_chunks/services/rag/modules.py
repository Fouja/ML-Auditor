"""
Pluggable RAG source modules.

Each module knows one data-source family (emails, calendar, Kijiji, ...), can
apply a small relevance boost to its own hits, and annotates hits with
source-specific context that the orchestrator surfaces in API responses and
agent tool results. New sources are added by registering another module here —
the retriever and orchestrator do not need to change.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SourceModule:
    name: str
    source_types: list[str] = field(default_factory=list)
    boost: float = 0.0

    def annotate(self, hit: dict) -> dict:
        """Add module-specific context to a hit (no-op by default)."""
        return dict(hit)

    def reweight(self, hit: dict) -> float:
        """Optionally adjust a hit's score; default returns it unchanged."""
        return float(hit.get("score", 0.0))


class _EmailModule(SourceModule):
    def __init__(self):
        super().__init__(
            name="email",
            source_types=["email", "gmail"],
            boost=0.0,
        )

    def annotate(self, hit: dict) -> dict:
        meta = hit.get("metadata") or {}
        enriched = dict(hit)
        context = enriched.setdefault("module_context", {})
        context["thread"] = meta.get("message_id")
        context["subject"] = meta.get("subject")
        context["sender"] = meta.get("sender")
        context["category"] = meta.get("category") or hit.get("category")
        context["subcategory"] = meta.get("subcategory")
        context["confidence"] = meta.get("confidence")
        return enriched

    def reweight(self, hit: dict) -> float:
        score = float(hit.get("score", 0.0))
        confidence = (hit.get("metadata") or {}).get("confidence")
        if isinstance(confidence, (int, float)):
            score += (float(confidence) - 0.5) * 0.1
        return score


class _CalendarModule(SourceModule):
    def __init__(self):
        super().__init__(name="calendar", source_types=["google_calendar"], boost=0.02)

    def annotate(self, hit: dict) -> dict:
        meta = hit.get("metadata") or {}
        enriched = dict(hit)
        context = enriched.setdefault("module_context", {})
        context["event"] = {
            "start": meta.get("start"),
            "end": meta.get("end"),
            "location": meta.get("location"),
        }
        return enriched


class _KijijiModule(SourceModule):
    def __init__(self):
        super().__init__(name="kijiji", source_types=["kijiji"], boost=0.02)

    def annotate(self, hit: dict) -> dict:
        meta = hit.get("metadata") or {}
        enriched = dict(hit)
        context = enriched.setdefault("module_context", {})
        context["listing"] = {
            "price": meta.get("price"),
            "url": meta.get("url"),
            "location": meta.get("location"),
        }
        return enriched


class _JiraModule(SourceModule):
    def __init__(self):
        super().__init__(name="jira", source_types=["jira"], boost=0.01)

    def annotate(self, hit: dict) -> dict:
        meta = hit.get("metadata") or {}
        enriched = dict(hit)
        context = enriched.setdefault("module_context", {})
        context["issue"] = {
            "key": meta.get("issue_key") or meta.get("key"),
            "status": meta.get("status"),
            "project": meta.get("project"),
        }
        return enriched


class _PlaidModule(SourceModule):
    def __init__(self):
        super().__init__(name="plaid", source_types=["plaid"], boost=0.01)

    def annotate(self, hit: dict) -> dict:
        meta = hit.get("metadata") or {}
        enriched = dict(hit)
        context = enriched.setdefault("module_context", {})
        context["transaction"] = {
            "amount": meta.get("amount"),
            "merchant": meta.get("merchant_name"),
            "date": meta.get("date"),
        }
        return enriched


class _ManualModule(SourceModule):
    def __init__(self):
        super().__init__(name="manual", source_types=["manual"], boost=0.0)

    def annotate(self, hit: dict) -> dict:
        enriched = dict(hit)
        enriched.setdefault("module_context", {})["source"] = "manual"
        return enriched


SOURCE_MODULES: list[SourceModule] = [
    _EmailModule(),
    _CalendarModule(),
    _KijijiModule(),
    _JiraModule(),
    _PlaidModule(),
    _ManualModule(),
]


def modules_for_sources(sources: list[str] | None) -> list[SourceModule]:
    """Modules matching the requested source types (all modules if none given)."""
    if not sources:
        return SOURCE_MODULES
    wanted = set(sources)
    matched = [m for m in SOURCE_MODULES if set(m.source_types) & wanted]
    return matched or SOURCE_MODULES
