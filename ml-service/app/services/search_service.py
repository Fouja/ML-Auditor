"""
Search service for document retrieval and RAG.
"""

from typing import List, Dict, Any, Optional
import structlog

from app.services.nim_service import nim_service

logger = structlog.get_logger()


class SearchService:
    """
    Service for document search and RAG context generation.
    """

    async def search_documents(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search documents using semantic similarity.

        Args:
            query: Search query
            limit: Max results
            filters: Optional filters (user_id, data_type)

        Returns:
            List of matching documents
        """
        try:
            # Generate query embedding
            query_embedding = await nim_service.generate_embedding(query)

            # Search via database (simulated for now)
            # In production, would use pgvector similarity search
            results = await self._vector_search(
                query_embedding=query_embedding,
                limit=limit,
                filters=filters or {},
            )

            logger.info(f"Search for '{query}' returned {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Search error: {e}")
            raise

    async def _vector_search(
        self,
        query_embedding: List[float],
        limit: int,
        filters: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Perform vector similarity search.
        """
        # Simulated results for now
        # In production, use pgvector:
        # SELECT * FROM document_chunks
        # ORDER BY embedding <=> query_embedding
        # LIMIT limit

        return []

    async def get_rag_context(
        self,
        query: str,
        user_id: Optional[str] = None,
        max_chunks: int = 5,
    ) -> Dict[str, Any]:
        """
        Get RAG context for a query.

        Args:
            query: User query
            user_id: Optional user filter
            max_chunks: Max chunks to return

        Returns:
            Dict with context and sources
        """
        try:
            # Search for relevant documents
            filters = {}
            if user_id:
                filters["user_id"] = user_id

            results = await self.search_documents(
                query=query,
                limit=max_chunks,
                filters=filters,
            )

            # Build context
            context_parts = []
            sources = []

            for doc in results:
                context_parts.append(doc.get("content", ""))
                sources.append({
                    "id": doc.get("id"),
                    "type": doc.get("data_type"),
                    "relevance": doc.get("similarity", 0),
                })

            context = "\n\n---\n\n".join(context_parts)

            return {
                "context": context,
                "sources": sources,
                "chunk_count": len(results),
                "query": query,
            }

        except Exception as e:
            logger.error(f"RAG context error: {e}")
            raise

    async def extract_entities_from_text(
        self,
        text: str,
        entity_types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Extract named entities from text using NIM.

        Args:
            text: Text to analyze
            entity_types: Types of entities to extract

        Returns:
            List of extracted entities
        """
        try:
            entities = await nim_service.extract_entities(text)
            logger.info(f"Extracted {len(entities)} entities")
            return entities
        except Exception as e:
            logger.error(f"Entity extraction error: {e}")
            raise


# Singleton instance
search_service = SearchService()
