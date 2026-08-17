"""Embedding access for the RAG pipeline (query vs. passage input types).

Imports the generating module and calls through it (rather than binding the
function at import time) so tests can patch
``apps.document_chunks.services.embedding_generation._generate_embedding_sync``
and have the RAG pipeline pick the replacement up.
"""

from __future__ import annotations

from .. import embedding_generation


def embed_query(text: str) -> list[float]:
    """Embed a search query (asymmetric query prefix for nv-embedqa-e5-v5)."""
    return embedding_generation._generate_embedding_sync(text, input_type="query")


def embed_passage(text: str) -> list[float]:
    """Embed a stored document passage."""
    return embedding_generation._generate_embedding_sync(text, input_type="passage")
