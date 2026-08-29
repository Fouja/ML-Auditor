"""
sqlite-vec integration for the ML-Auditor desktop build.

The desktop app uses SQLite instead of Postgres+pgvector. sqlite-vec is a
run-time loadable SQLite extension that provides fast vector search. When it is
available we create a small virtual table that mirrors the embeddings stored in
``DocumentChunk.embedding`` (JSON text on SQLite) and run cosine-distance search
in SQL. When sqlite-vec is unavailable we fall back to the existing Python
numpy-style cosine scan.
"""

from __future__ import annotations

import logging

from django.db import connection

logger = logging.getLogger(__name__)

# Dimensionality must match the model / EmbeddingVectorField configuration.
_DIMENSIONS = 1024


def _execute(sql: str, params=None):
    with connection.cursor() as cursor:
        cursor.execute(sql, params or ())


def _ensure_extension() -> bool:
    """Return True if sqlite-vec extension is loaded, otherwise False."""
    if connection.vendor != "sqlite":
        return False
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT vec_version()")
            return True
    except Exception:
        return False


def _table_exists(name: str) -> bool:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=%s",
            [name],
        )
        return cursor.fetchone() is not None


def ensure_vector_table() -> bool:
    """Create the sqlite-vec virtual table if sqlite-vec is available.

    Returns True if the table is ready to use.
    """
    if not _ensure_extension():
        return False

    if not _table_exists("document_chunks_vec"):
        try:
            _execute(
                f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS document_chunks_vec USING vec0(
                    chunk_id INTEGER PRIMARY KEY,
                    embedding FLOAT[{_DIMENSIONS}]
                )
                """
            )
        except Exception as exc:
            logger.warning("sqlite-vec: could not create virtual table: %s", exc)
            return False

    return True


def sync_missing_embeddings() -> int:
    """Copy embeddings from DocumentChunk rows into the sqlite-vec virtual table.

    Returns the number of rows inserted/updated.
    """
    if not ensure_vector_table():
        return 0

    try:
        _execute(
            """
            INSERT OR REPLACE INTO document_chunks_vec (chunk_id, embedding)
            SELECT dc.id, vec_f32(dc.embedding)
            FROM document_chunks_documentchunk dc
            LEFT JOIN document_chunks_vec v ON v.chunk_id = dc.id
            WHERE dc.embedding IS NOT NULL AND dc.embedding != ''
              AND v.chunk_id IS NULL
            """
        )
        with connection.cursor() as cursor:
            return cursor.rowcount
    except Exception as exc:
        logger.warning("sqlite-vec: could not sync embeddings: %s", exc)
        return 0


def search(
    query_vec: list[float],
    user_id: int,
    *,
    sources: list[str] | None = None,
    categories: list[str] | None = None,
    since=None,
    limit: int = 10,
    min_score: float = 0.30,
) -> list[dict]:
    """Return ranked DocumentChunk hits using sqlite-vec cosine distance.

    Falls back to an empty list if sqlite-vec is unavailable or fails.
    """
    if not ensure_vector_table():
        return []

    sync_missing_embeddings()

    params: list = [query_vec]
    where_clauses = ["v.chunk_id = dc.id", "dc.stream_id = s.id", "s.user_id = %s"]
    params.append(user_id)

    if sources:
        placeholders = ",".join(["%s"] * len(sources))
        where_clauses.append(f"s.source_type IN ({placeholders})")
        params.extend(sources)

    if categories:
        placeholders = ",".join(["%s"] * len(categories))
        where_clauses.append(f"dc.cluster_category IN ({placeholders})")
        params.extend(categories)

    if since is not None:
        where_clauses.append("dc.created_at >= %s")
        params.append(since)

    where_sql = " AND ".join(where_clauses)

    sql = f"""
        SELECT
            dc.id,
            dc.content,
            dc.cluster_category,
            dc.metadata,
            dc.created_at,
            s.source_type,
            v.distance
        FROM document_chunks_vec v
        JOIN document_chunks_documentchunk dc ON dc.id = v.chunk_id
        JOIN document_chunks_documentstream s ON s.id = dc.stream_id
        WHERE {where_sql}
          AND v.embedding MATCH vec_f32(%s)
        ORDER BY v.distance
        LIMIT %s
    """
    params.extend([limit])

    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
    except Exception as exc:
        logger.warning("sqlite-vec search failed: %s", exc)
        return []

    hits = []
    for row in rows:
        chunk_id, content, category, metadata, created_at, source_type, distance = row
        score = 1.0 - float(distance)
        if score >= min_score:
            hits.append({
                "chunk_id": str(chunk_id),
                "content": content,
                "score": round(score, 4),
                "source_type": source_type,
                "category": category,
                "metadata": metadata or {},
                "created_at": created_at,
            })
    return hits
