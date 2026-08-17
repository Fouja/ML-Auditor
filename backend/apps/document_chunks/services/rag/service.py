"""
RAG orchestration service.

Composes the retriever (pgvector or in-process fallback), the source modules,
and — optionally — a grounded NIM answer into a single query API. Every query
emits a ``rag_query`` structured metric (latency, backend, result counts,
source distribution) via the ``apps.metrics`` logger so the JSON log formatter
ships it to the observability stack.
"""

from __future__ import annotations

import logging
import time

from .modules import modules_for_sources
from .retriever import retrieve

logger = logging.getLogger(__name__)

METRICS_LOGGER = logging.getLogger("apps.metrics")


def _emit(event: str, data: dict) -> None:
    METRICS_LOGGER.info(event, extra={"metrics": data})


def _source_distribution(hits: list[dict]) -> dict[str, int]:
    dist: dict[str, int] = {}
    for hit in hits:
        src = hit.get("source_type") or "unknown"
        dist[src] = dist.get(src, 0) + 1
    return dist


def _grounded_answer(query: str, hits: list[dict]) -> str | None:
    """Answer strictly from the retrieved chunks, citing them as [n]."""
    if not hits:
        return None
    try:
        import httpx
        from django.conf import settings
        from apps.integrations.models import LLMConfiguration

        api_key = getattr(settings, "NIM_API_KEY", "")
        if not api_key:
            cfg = LLMConfiguration.objects.filter(provider="nvidia", is_active=True).first()
            if cfg:
                api_key = cfg.decrypted_api_key
        if not api_key:
            return None

        base_url = getattr(settings, "NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
        model = getattr(settings, "NIM_MODEL", "meta/llama-3.1-8b-instruct")

        context = "\n\n".join(
            f"[{i + 1}] {hit['content'][:1500]}" for i, hit in enumerate(hits[:5])
        )
        prompt = (
            "Answer the question using ONLY the provided sources. "
            "Cite each claim with its source number like [1]. "
            'If the sources do not contain the answer, reply "No answer in the sources".\n\n'
            f"Question: {query}\n\nSources:\n{context}"
        )
        with httpx.Client(timeout=20) as client:
            resp = client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 300,
                    "temperature": 0.2,
                },
            )
            resp.raise_for_status()
            return (resp.json()["choices"][0]["message"]["content"] or "").strip() or None
    except Exception as exc:
        logger.warning(f"Grounded answer generation failed: {exc}")
        return None


def query_rag(
    user,
    query: str,
    *,
    sources: list[str] | None = None,
    categories: list[str] | None = None,
    limit: int = 10,
    min_score: float = 0.30,
    answer: bool = False,
    since=None,
) -> dict:
    """Full RAG query: ranked hits (+ optional grounded answer) + metadata.

    Returns::

        {
            "query": str,
            "results": [hit, ...],       # each enriched by its source module
            "answer": str | None,        # only when answer=True and NIM responds
            "backend": "pgvector" | "python" | "keyword",
            "source_distribution": {source_type: count},
            "latency_ms": float,
        }
    """
    started = time.perf_counter()
    try:
        hits, backend = retrieve(
            user,
            query,
            sources=sources,
            categories=categories,
            limit=limit,
            min_score=min_score,
            since=since,
        )

        modules = modules_for_sources(sources)
        module_by_source = {src: m for m in modules for src in m.source_types}
        enriched = []
        for hit in hits:
            module = module_by_source.get(hit.get("source_type"))
            if module is not None:
                hit["score"] = round(module.reweight(hit), 4)
                hit = module.annotate(hit)
            enriched.append(hit)
        enriched.sort(key=lambda h: h.get("score", 0.0), reverse=True)

        grounded = _grounded_answer(query, enriched) if answer else None

        payload = {
            "query": query,
            "results": enriched,
            "answer": grounded,
            "backend": backend,
            "source_distribution": _source_distribution(enriched),
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        }
        _emit("rag_query", {
            "query": query,
            "user_id": str(getattr(user, "id", "")),
            "backend": backend,
            "sources": sources,
            "categories": categories,
            "limit": limit,
            "min_score": min_score,
            "results": len(enriched),
            "source_distribution": payload["source_distribution"],
            "latency_ms": payload["latency_ms"],
            "answer_generated": grounded is not None,
        })
        return payload
    except Exception as exc:
        logger.exception("RAG query failed")
        payload = {
            "query": query,
            "results": [],
            "answer": None,
            "backend": "error",
            "source_distribution": {},
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "error": str(exc),
        }
        _emit("rag_query_error", {
            "query": query,
            "user_id": str(getattr(user, "id", "")),
            "error": str(exc),
        })
        return payload
