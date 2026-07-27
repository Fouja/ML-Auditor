"""
API routes for ML Service.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import structlog

from app.services.email_analysis import email_analysis_service
from app.services.financial_analysis import financial_analysis_service
from app.services.embedding_service import embedding_service
from app.services.search_service import search_service
from app.services.crewai_agents import kijiji_agent

logger = structlog.get_logger()

router = APIRouter()


# Request/Response models
class EmailAnalysisRequest(BaseModel):
    content: str
    subject: str = ""
    sender: str = ""
    user_id: Optional[str] = None


class EmailAnalysisResponse(BaseModel):
    category: str
    confidence: float
    reasoning: str
    entities: List[Dict[str, Any]]
    priority: str
    embedding: List[float]
    metadata: Dict[str, Any]


class AnomalyDetectionRequest(BaseModel):
    transactions: List[Dict[str, Any]]
    user_id: Optional[str] = None


class AnomalyDetectionResponse(BaseModel):
    anomalies: List[Dict[str, Any]]
    total_transactions: int
    anomalies_found: int
    anomaly_rate: float
    model_trained: bool
    summary: str


class EmbeddingRequest(BaseModel):
    texts: List[str]


class EmbeddingResponse(BaseModel):
    embeddings: List[List[float]]
    count: int


class KijijiAnalysisRequest(BaseModel):
    message: str
    listing_price: float = 0


class KijijiAnalysisResponse(BaseModel):
    is_spam: bool
    is_genuine: bool
    is_lowball: bool
    confidence: float
    suggested_response: Optional[str]
    listing_price: float


class ChunkEmailRequest(BaseModel):
    content: str
    chunk_size: int = 500
    overlap: int = 50


class ChunkEmailResponse(BaseModel):
    chunks: List[Dict[str, Any]]
    total_chunks: int
    total_length: int


class SearchRequest(BaseModel):
    query: str
    limit: int = 10
    filters: Optional[Dict[str, Any]] = None


class SearchResult(BaseModel):
    id: str
    content: str
    data_type: str
    similarity: float
    metadata: Dict[str, Any]


class SearchResponse(BaseModel):
    results: List[SearchResult]
    query: str
    count: int


class RAGContextRequest(BaseModel):
    query: str
    user_id: Optional[str] = None
    max_chunks: int = 5


class RAGContextResponse(BaseModel):
    context: str
    sources: List[Dict[str, Any]]
    chunk_count: int
    query: str


# Email Analysis endpoints
@router.post("/analyze-email", response_model=EmailAnalysisResponse)
async def analyze_email(request: EmailAnalysisRequest):
    """
    Analyze an email for classification and entity extraction.

    - **content**: Email body content
    - **subject**: Email subject
    - **sender**: Email sender
    - **user_id**: Optional user ID for context
    """
    try:
        result = await email_analysis_service.analyze_email(
            content=request.content,
            subject=request.subject,
            sender=request.sender,
            user_id=request.user_id,
        )
        return EmailAnalysisResponse(**result)
    except Exception as e:
        logger.error(f"Email analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-emails-batch")
async def analyze_emails_batch(
    emails: List[EmailAnalysisRequest],
    user_id: Optional[str] = None,
):
    """
    Analyze multiple emails in batch.
    """
    try:
        results = await email_analysis_service.batch_analyze(
            emails=[e.model_dump() for e in emails],
            user_id=user_id,
        )
        return {"results": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Batch email analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Anomaly Detection endpoints
@router.post("/detect-anomalies", response_model=AnomalyDetectionResponse)
async def detect_anomalies(request: AnomalyDetectionRequest):
    """
    Detect anomalies in financial transactions using Isolation Forest.

    - **transactions**: List of transaction dicts with amount, date, category
    - **user_id**: Optional user ID
    """
    try:
        result = await financial_analysis_service.detect_anomalies(
            transactions=request.transactions,
            user_id=request.user_id,
        )
        return AnomalyDetectionResponse(**result)
    except Exception as e:
        logger.error(f"Anomaly detection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/financial-insights")
async def financial_insights(
    transactions: List[Dict[str, Any]],
    user_id: Optional[str] = None,
):
    """
    Get financial insights including correlations and subscriptions.
    """
    try:
        result = await financial_analysis_service.analyze_correlations(
            transactions=transactions,
            user_id=user_id,
        )
        return result
    except Exception as e:
        logger.error(f"Financial insights error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Embedding endpoints
@router.post("/generate-embeddings", response_model=EmbeddingResponse)
async def generate_embeddings(request: EmbeddingRequest):
    """
    Generate embeddings for a list of texts.

    - **texts**: List of texts to embed
    """
    try:
        embeddings = await embedding_service.generate_embeddings_batch(request.texts)
        return EmbeddingResponse(embeddings=embeddings, count=len(embeddings))
    except Exception as e:
        logger.error(f"Embedding generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chunk-and-embed")
async def chunk_and_embed(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50,
):
    """
    Chunk text and generate embeddings for each chunk.
    """
    try:
        results = await embedding_service.chunk_and_embed(
            text=text,
            chunk_size=chunk_size,
            overlap=overlap,
        )
        return {"chunks": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Chunk and embed error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Kijiji Analysis endpoints
@router.post("/analyze-kijiji-message", response_model=KijijiAnalysisResponse)
async def analyze_kijiji_message(request: KijijiAnalysisRequest):
    """
    Analyze a Kijiji message for spam/negotiation.

    - **message**: Message content
    - **listing_price**: Original listing price
    """
    try:
        result = await kijiji_agent.analyze_message(
            message=request.message,
            listing_price=request.listing_price,
        )
        return KijijiAnalysisResponse(**result)
    except Exception as e:
        logger.error(f"Kijiji analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Health check
@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "ml-api"}


# Chunk Email endpoint
@router.post("/chunk-email", response_model=ChunkEmailResponse)
async def chunk_email(request: ChunkEmailRequest):
    """
    Chunk email content into smaller pieces for processing.

    - **content**: Email content to chunk
    - **chunk_size**: Maximum chunk size (default 500)
    - **overlap**: Overlap between chunks (default 50)
    """
    try:
        results = await embedding_service.chunk_and_embed(
            text=request.content,
            chunk_size=request.chunk_size,
            overlap=request.overlap,
        )

        return ChunkEmailResponse(
            chunks=results,
            total_chunks=len(results),
            total_length=len(request.content),
        )
    except Exception as e:
        logger.error(f"Email chunking error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Search endpoints
@router.post("/search-documents", response_model=SearchResponse)
async def search_documents(request: SearchRequest):
    """
    Search documents using semantic similarity.

    - **query**: Search query
    - **limit**: Maximum number of results (default 10)
    - **filters**: Optional filters (user_id, data_type)
    """
    try:
        results = await search_service.search_documents(
            query=request.query,
            limit=request.limit,
            filters=request.filters,
        )

        return SearchResponse(
            results=[SearchResult(**r) for r in results],
            query=request.query,
            count=len(results),
        )
    except Exception as e:
        logger.error(f"Document search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rag-context", response_model=RAGContextResponse)
async def get_rag_context(request: RAGContextRequest):
    """
    Get RAG context for a query.

    - **query**: User query
    - **user_id**: Optional user ID to filter results
    - **max_chunks**: Maximum number of chunks to return (default 5)
    """
    try:
        result = await search_service.get_rag_context(
            query=request.query,
            user_id=request.user_id,
            max_chunks=request.max_chunks,
        )

        return RAGContextResponse(**result)
    except Exception as e:
        logger.error(f"RAG context error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Batch Embedding Job endpoint
@router.post("/batch-embedding-job")
async def batch_embedding_job(
    document_ids: List[str],
    user_id: Optional[str] = None,
):
    """
    Process batch embedding job for multiple documents.

    - **document_ids**: List of document IDs to process
    - **user_id**: Optional user ID for context
    """
    try:
        results = []

        for doc_id in document_ids:
            # Simulate embedding generation for each document
            # In production, would fetch document content and generate embeddings
            results.append({
                "document_id": doc_id,
                "status": "queued",
                "user_id": user_id,
            })

        logger.info(f"Batch embedding job queued for {len(document_ids)} documents")

        return {
            "status": "queued",
            "document_count": len(document_ids),
            "documents": results,
        }
    except Exception as e:
        logger.error(f"Batch embedding job error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
