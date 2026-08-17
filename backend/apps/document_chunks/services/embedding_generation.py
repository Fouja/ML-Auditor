"""
Embedding generation job for creating vector embeddings.
Uses NVIDIA NIM for embedding generation via the OpenAI-compatible endpoint.
"""

import logging

import httpx
from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)

NIM_BASE_URL = getattr(settings, "NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
NIM_API_KEY = getattr(settings, "NIM_API_KEY", "")
EMBEDDING_MODEL = "nvidia/nv-embedqa-e5-v5"

DIMENSIONS = 1024


def _get_api_key() -> str:
    """Get NIM API key from settings or any active LLM config."""
    if NIM_API_KEY:
        return NIM_API_KEY
    try:
        from django.db.models import Q
        from apps.integrations.models import LLMConfiguration

        config = (
            LLMConfiguration.objects.filter(
                Q(provider="nvidia") | Q(provider="openai"),
                is_active=True,
            )
            .exclude(api_key="")
            .first()
        )
        if config:
            return config.decrypted_api_key
    except Exception:
        pass
    return ""


def _generate_embedding_sync(text: str, input_type: str = "passage") -> list[float]:
    """Generate an embedding via NIM.

    Args:
        text: Text to embed.
        input_type: "passage" for stored documents, "query" for search queries.
            Required for asymmetric models like nv-embedqa-e5-v5.
    """
    api_key = _get_api_key()
    if not api_key:
        return [0.0] * DIMENSIONS

    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(
                f"{NIM_BASE_URL}/embeddings",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": EMBEDDING_MODEL,
                    "input": text[:8192],
                    "input_type": input_type,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["data"][0]["embedding"]
    except Exception as e:
        logger.warning(f"Embedding generation failed, using fallback: {e}")
        return [0.0] * DIMENSIONS


@shared_task(bind=True, max_retries=3)
def generate_embedding_job(self, chunk_id: str):
    from apps.document_chunks.models import DocumentChunk

    try:
        chunk = DocumentChunk.objects.get(id=chunk_id)
        embedding = _generate_embedding_sync(chunk.content)
        chunk.embedding = embedding
        chunk.save()
        logger.info(f"Embedding generated for chunk {chunk_id}")
        return {"status": "success", "chunk_id": chunk_id}
    except DocumentChunk.DoesNotExist:
        logger.error(f"Chunk {chunk_id} not found")
        return {"error": "Chunk not found"}
    except Exception as exc:
        logger.error(f"Error generating embedding: {exc}")
        self.retry(exc=exc, countdown=60)
        return {"error": str(exc)}


@shared_task(bind=True, max_retries=3)
def generate_embeddings_batch(self, stream_id: str):
    from apps.document_chunks.models import DocumentChunk

    try:
        chunks = DocumentChunk.objects.filter(stream_id=stream_id)
        for chunk in chunks:
            generate_embedding_job.delay(str(chunk.id))
        logger.info(f"Batch embedding generation started for stream {stream_id}")
        return {"status": "success", "chunks_count": chunks.count()}
    except Exception as exc:
        logger.error(f"Error in batch embedding: {exc}")
        self.retry(exc=exc, countdown=60)
        return {"error": str(exc)}
