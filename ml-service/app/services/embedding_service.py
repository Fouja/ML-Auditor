"""
Embedding service for ML-Auditor.
Generates and manages vector embeddings using NVIDIA NIM.
"""

from typing import List, Optional
import structlog

from app.services.nim_service import nim_service

logger = structlog.get_logger()


class EmbeddingService:
    """
    Service for generating and managing embeddings.
    """

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector (384 dimensions)
        """
        try:
            embedding = await nim_service.generate_embedding(text)
            logger.info(f"Generated embedding for text ({len(text)} chars)")
            return embedding
        except Exception as e:
            logger.error(f"Embedding generation error: {e}")
            raise

    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        try:
            embeddings = await nim_service.generate_embeddings_batch(texts)
            logger.info(f"Generated {len(embeddings)} embeddings")
            return embeddings
        except Exception as e:
            logger.error(f"Batch embedding error: {e}")
            raise

    async def chunk_and_embed(
        self,
        text: str,
        chunk_size: int = 500,
        overlap: int = 50,
    ) -> List[dict]:
        """
        Chunk text and generate embeddings for each chunk.

        Args:
            text: Text to chunk and embed
            chunk_size: Maximum chunk size
            overlap: Overlap between chunks

        Returns:
            List of chunk dicts with content and embedding
        """
        # Split text into chunks
        chunks = []
        words = text.split()

        for i in range(0, len(words), chunk_size - overlap):
            chunk_words = words[i : i + chunk_size]
            chunk_text = " ".join(chunk_words)
            chunks.append(chunk_text)

        # Generate embeddings for all chunks
        embeddings = await self.generate_embeddings_batch(chunks)

        # Combine chunks with embeddings
        results = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            results.append({
                "chunk_index": i,
                "content": chunk,
                "embedding": embedding,
                "total_chunks": len(chunks),
            })

        return results

    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Similarity score (0-1)
        """
        import numpy as np

        vec1 = np.array(vec1)
        vec2 = np.array(vec2)

        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))


# Singleton instance
embedding_service = EmbeddingService()
