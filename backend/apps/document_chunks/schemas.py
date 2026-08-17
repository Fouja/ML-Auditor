"""
Pydantic schemas for DocumentChunk API.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from ninja import Schema


class DocumentChunkResponse(Schema):
    """Schema for document chunk response."""

    id: UUID
    content: str
    cluster_category: str
    chunk_index: int
    total_chunks: int
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    stream_id: UUID

    @staticmethod
    def resolve_id(obj):
        return obj.id


class DocumentChunkSearch(Schema):
    """Schema for semantic search."""

    query: str
    limit: int = 10
    cluster_category: Optional[str] = None


class SearchResult(Schema):
    """Schema for search result."""

    chunk: DocumentChunkResponse
    score: float


class DocumentChunkListResponse(Schema):
    """Schema for paginated document chunk list."""

    items: List[DocumentChunkResponse]
    total: int
    page: int
    pages: int


class RagQuery(Schema):
    """Schema for RAG retrieval query."""

    query: str
    sources: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    limit: int = 10
    min_score: float = 0.30
    answer: bool = False


class RagResult(Schema):
    """Schema for a single RAG retrieval hit."""

    chunk_id: str
    content: str
    score: float
    source_type: str
    category: str
    metadata: Optional[Dict[str, Any]] = None
    module_context: Optional[Dict[str, Any]] = None


class RagResponse(Schema):
    """Schema for RAG query response."""

    query: str
    results: List[RagResult]
    answer: Optional[str] = None
    backend: str
    source_distribution: Dict[str, int]
    latency_ms: float
