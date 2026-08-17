"""
DocumentChunk API endpoints for ML-Auditor.
"""

from typing import List

from django.core.paginator import Paginator
from ninja import Query, Router
from ninja.errors import HttpError

from .models import DocumentChunk
from .schemas import (
    DocumentChunkListResponse,
    DocumentChunkResponse,
    RagQuery,
    RagResponse,
    SearchResult,
)

router = Router()


@router.get("/", response=DocumentChunkListResponse)
def list_document_chunks(
    request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    cluster_category: str = Query(None),
):
    """List document chunks for current user's data streams."""
    queryset = DocumentChunk.objects.filter(stream__user=request.auth)

    if cluster_category:
        queryset = queryset.filter(cluster_category=cluster_category)

    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)

    return DocumentChunkListResponse(
        items=list(page_obj),
        total=paginator.count,
        page=page,
        pages=paginator.num_pages,
    )


@router.get("/{chunk_id}", response=DocumentChunkResponse)
def get_document_chunk(request, chunk_id: str):
    """Get document chunk by ID."""
    try:
        chunk = DocumentChunk.objects.get(
            id=chunk_id,
            stream__user=request.auth,
        )
        return chunk
    except DocumentChunk.DoesNotExist:
        raise HttpError(404, "Document chunk not found")


@router.post("/search", response=List[SearchResult])
def search_documents(request, payload: dict):
    """Semantic search across document chunks."""
    query = payload.get("query", "")
    limit = payload.get("limit", 10)
    cluster_category = payload.get("cluster_category")

    # Basic text search for now (will be enhanced with vector search later)
    queryset = DocumentChunk.objects.filter(
        stream__user=request.auth,
        content__icontains=query,
    )

    if cluster_category:
        queryset = queryset.filter(cluster_category=cluster_category)

    chunks = queryset[:limit]

    results = []
    for chunk in chunks:
        results.append(
            SearchResult(
                chunk=chunk,
                score=1.0,  # Placeholder score
            )
        )

    return results


@router.post("/rag/query", response=RagResponse)
def rag_query(request, payload: RagQuery):
    """Vector RAG query over the user's document chunks.

    Runs the modular RAG pipeline (pgvector ``<=>`` on Postgres, in-process
    cosine on SQLite, keyword fallback) with optional source modules and a
    grounded NIM answer.
    """
    from .services.rag.service import query_rag

    result = query_rag(
        request.auth,
        payload.query,
        sources=payload.sources,
        categories=payload.categories,
        limit=payload.limit,
        min_score=payload.min_score,
        answer=payload.answer,
    )
    if "error" in result:
        raise HttpError(502, result["error"])
    return RagResponse(**result)


@router.delete("/{chunk_id}")
def delete_document_chunk(request, chunk_id: str):
    """Delete document chunk."""
    try:
        chunk = DocumentChunk.objects.get(
            id=chunk_id,
            stream__user=request.auth,
        )
        chunk.delete()
        return {"success": True}
    except DocumentChunk.DoesNotExist:
        raise HttpError(404, "Document chunk not found")
