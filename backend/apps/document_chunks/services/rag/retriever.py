"""
RAG retriever: turns a query into ranked DocumentChunks.

Backend selection:
  * Postgres (production): real pgvector ``<=>`` cosine distance executed in SQL
    through pgvector.django's CosineDistance, backed by the HNSW index.
  * SQLite (tests): no vector type, so the field stores JSON floats and we run
    an in-process numpy cosine scan over the user's chunks.

If the query embedding is unavailable (zero vector from a NIM failure) or the
vector search returns nothing, a keyword ``icontains`` fallback over the query's
significant tokens keeps the endpoint useful.
"""

from __future__ import annotations

import logging
import math
import re
import time

from django.db import connection

from .embedding_source import embed_query

logger = logging.getLogger(__name__)
METRICS_LOGGER = logging.getLogger("apps.metrics")

_MIN_SCORE = 0.30
_MAX_LIMIT = 50
_STOP_TOKENS = {"a", "an", "the", "and", "or", "of", "to", "for", "in", "on", "at", "with", "my", "your", "i", "me", "is", "are", "was", "were", "about"}

_HIT_KEYS = ("chunk_id", "content", "score", "source_type", "category", "metadata", "created_at")


def _log_retrieval(user, query: str, method: str, hits: list, limit: int, latency_ms: float):
    """Emit structured telemetry for every RAG retrieval."""
    source_types = sorted({h.get("source_type") for h in hits if h.get("source_type")})
    categories = sorted({h.get("category") for h in hits if h.get("category")})
    try:
        from apps.document_chunks.services.embedding_generation import DIMENSIONS, EMBEDDING_MODEL
        dimensions = DIMENSIONS
        embedding_model = EMBEDDING_MODEL
    except Exception:
        dimensions = 1024
        embedding_model = "unknown"

    METRICS_LOGGER.info(
        "rag_retrieval",
        extra={
            "metrics": {
                "metric": "rag_retrieval",
                "metric_type": "rag",
                "agent_action": "pgvector_search",
                "search_query": query[:500],
                "search_method": method,
                "embedding_model": embedding_model,
                "dimensions": dimensions,
                "top_k": limit,
                "results_returned": len(hits),
                "source_types": source_types,
                "cluster_categories": categories,
                "latency_ms": latency_ms,
                "user_id": str(getattr(user, "id", "")),
            }
        },
    )


def _is_all_zero(embedding) -> bool:
    if embedding is None:
        return True
    if hasattr(embedding, "sum"):
        return float(embedding.sum()) == 0.0
    return all(v == 0.0 for v in embedding)


def _cosine(a, b) -> float:
    """Cosine similarity of two float sequences."""
    if _is_all_zero(a) or _is_all_zero(b):
        return 0.0
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _hit(chunk, score: float) -> dict:
    return {
        "chunk_id": str(chunk.id),
        "content": chunk.content,
        "score": round(float(score), 4),
        "source_type": chunk.stream.source_type,
        "category": chunk.cluster_category,
        "metadata": chunk.metadata or {},
        "created_at": chunk.created_at,
    }


def _build_queryset(user, *, sources=None, categories=None, since=None):
    from apps.document_chunks.models import DocumentChunk

    qs = DocumentChunk.objects.filter(stream__user=user)
    if sources:
        qs = qs.filter(stream__source_type__in=sources)
    if categories:
        qs = qs.filter(cluster_category__in=categories)
    if since is not None:
        qs = qs.filter(created_at__gte=since)
    return qs


def _retrieve_pgvector(user, query_vec, *, sources=None, categories=None, since=None, limit=10, min_score=_MIN_SCORE) -> list[dict]:
    """Real pgvector search via ``<=>`` cosine distance on Postgres."""
    from pgvector.django import CosineDistance

    qs = _build_queryset(
        user, sources=sources, categories=categories, since=since
    ).annotate(distance=CosineDistance("embedding", query_vec))
    qs = qs.filter(distance__lte=1.0 - min_score).order_by("distance")[:limit]

    hits = []
    for chunk in qs:
        distance = getattr(chunk, "distance", None)
        if distance is None:
            distance = 1.0
        hits.append(_hit(chunk, 1.0 - float(distance)))
    return hits


def _retrieve_sqlite_vec(user, query_vec, *, sources=None, categories=None, since=None, limit=10, min_score=_MIN_SCORE) -> list[dict]:
    """Native sqlite-vec cosine distance search (desktop SQLite path)."""
    from . import sqlite_vec

    return sqlite_vec.search(
        list(query_vec),
        user.id,
        sources=sources,
        categories=categories,
        since=since,
        limit=limit,
        min_score=min_score,
    )


def _retrieve_python(user, query_vec, *, sources=None, categories=None, since=None, limit=10, min_score=_MIN_SCORE) -> list[dict]:
    """In-process numpy cosine scan (SQLite/test fallback)."""
    qs = _build_queryset(user, sources=sources, categories=categories, since=since)
    scored = []
    for chunk in qs.only("id", "content", "embedding", "cluster_category", "metadata", "created_at", "stream"):
        embedding = chunk.embedding
        if _is_all_zero(embedding):
            continue
        score = _cosine(list(query_vec), list(embedding))
        if score >= min_score:
            scored.append((score, chunk))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [_hit(chunk, score) for score, chunk in scored[:limit]]


def _retrieve_keyword(user, query, *, sources=None, categories=None, since=None, limit=10) -> list[dict]:
    """icontains fallback over the significant query tokens."""
    tokens = [t for t in re.findall(r"[a-zA-Z0-9_.#-]{3,}", query.lower()) if t not in _STOP_TOKENS]
    qs = _build_queryset(user, sources=sources, categories=categories, since=since)
    scored = []
    for token in tokens:
        token_qs = qs.filter(content__icontains=token)
        for chunk in token_qs.only("id", "content", "cluster_category", "metadata", "created_at", "stream")[:20]:
            scored.append((token_qs.filter(id=chunk.id).count() / max(len(tokens), 1), chunk))
    merged = {}
    for score, chunk in scored:
        key = str(chunk.id)
        if key not in merged:
            merged[key] = _hit(chunk, 0.0)
        merged[key]["score"] = round(merged[key]["score"] + score / 2.0, 4)
    return sorted(merged.values(), key=lambda h: h["score"], reverse=True)[:limit]


def retrieve(user, query, *, sources=None, categories=None, since=None, limit=10, min_score=_MIN_SCORE, hybrid=True) -> tuple[list[dict], str]:
    """Ranked search hits plus the backend tag (``pgvector`` | ``python`` | ``keyword``).

    ``limit`` is clamped to ``_MAX_LIMIT``; ``min_score`` to ``[0, 1]``.
    """
    start = time.monotonic()
    limit = max(1, min(int(limit), _MAX_LIMIT))
    min_score = max(0.0, min(float(min_score), 1.0))
    query = (query or "").strip()

    if not query:
        return [], "keyword"

    query_vec = embed_query(query)
    if not _is_all_zero(query_vec) and connection.vendor == "postgresql":
        hits = _retrieve_pgvector(
            user, query_vec, sources=sources, categories=categories,
            since=since, limit=limit, min_score=min_score,
        )
        method = "pgvector_cosine"
        if hits or not hybrid:
            latency_ms = round((time.monotonic() - start) * 1000)
            _log_retrieval(user, query, method, hits, limit, latency_ms)
            return hits, "pgvector"
    elif not _is_all_zero(query_vec):
        # Desktop/SQLite path: try sqlite-vec first, then fall back to Python cosine.
        sqlite_hits = _retrieve_sqlite_vec(
            user, query_vec, sources=sources, categories=categories,
            since=since, limit=limit, min_score=min_score,
        )
        if sqlite_hits:
            latency_ms = round((time.monotonic() - start) * 1000)
            _log_retrieval(user, query, "sqlite_vec_cosine", sqlite_hits, limit, latency_ms)
            return sqlite_hits, "sqlite-vec"

        hits = _retrieve_python(
            user, query_vec, sources=sources, categories=categories,
            since=since, limit=limit, min_score=min_score,
        )
        method = "python_cosine"
        if hits or not hybrid:
            latency_ms = round((time.monotonic() - start) * 1000)
            _log_retrieval(user, query, method, hits, limit, latency_ms)
            return hits, "python"

    hits = _retrieve_keyword(
        user, query, sources=sources, categories=categories, since=since, limit=limit
    )
    method = "keyword_fallback"
    latency_ms = round((time.monotonic() - start) * 1000)
    _log_retrieval(user, query, method, hits, limit, latency_ms)
    return hits, "keyword"
