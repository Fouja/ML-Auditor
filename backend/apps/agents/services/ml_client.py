"""
HTTP client for calling the ML microservice.
"""

import logging

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


class MLServiceClient:
    """
    Client for communicating with the ML microservice.
    """

    def __init__(self):
        self.base_url = getattr(settings, "ML_SERVICE_URL", "http://localhost:8001")

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        url = f"{self.base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()
                return response.json()
        except httpx.ConnectError:
            logger.warning(f"ML service unavailable at {url}")
            return {"error": "ML service unavailable"}
        except httpx.HTTPStatusError as e:
            logger.error(f"ML service error: {e.response.status_code}")
            return {"error": str(e)}

    async def analyze_email(
        self, content: str, subject: str = "", sender: str = "", user_id: str = None
    ) -> dict:
        return await self._request(
            "POST",
            "/api/v1/analyze-email",
            json={
                "content": content,
                "subject": subject,
                "sender": sender,
                "user_id": user_id,
            },
        )

    async def detect_anomalies(self, transactions: list, user_id: str = None) -> dict:
        return await self._request(
            "POST",
            "/api/v1/detect-anomalies",
            json={
                "transactions": transactions,
                "user_id": user_id,
            },
        )

    async def financial_insights(self, transactions: list, user_id: str = None) -> dict:
        return await self._request(
            "POST",
            "/api/v1/financial-insights",
            json={
                "transactions": transactions,
                "user_id": user_id,
            },
        )

    async def generate_embeddings(self, texts: list) -> dict:
        return await self._request(
            "POST",
            "/api/v1/generate-embeddings",
            json={
                "texts": texts,
            },
        )

    async def chunk_and_embed(
        self, text: str, chunk_size: int = 500, overlap: int = 50
    ) -> dict:
        return await self._request(
            "POST",
            "/api/v1/chunk-and-embed",
            json={
                "text": text,
                "chunk_size": chunk_size,
                "overlap": overlap,
            },
        )

    async def search_documents(
        self, query: str, limit: int = 10, filters: dict = None
    ) -> dict:
        return await self._request(
            "POST",
            "/api/v1/search-documents",
            json={
                "query": query,
                "limit": limit,
                "filters": filters,
            },
        )

    async def get_rag_context(
        self, query: str, user_id: str = None, max_chunks: int = 5
    ) -> dict:
        return await self._request(
            "POST",
            "/api/v1/rag-context",
            json={
                "query": query,
                "user_id": user_id,
                "max_chunks": max_chunks,
            },
        )

    async def analyze_kijiji_message(
        self, message: str, listing_price: float = 0
    ) -> dict:
        return await self._request(
            "POST",
            "/api/v1/analyze-kijiji-message",
            json={
                "message": message,
                "listing_price": listing_price,
            },
        )

    async def health_check(self) -> dict:
        return await self._request("GET", "/health")


ml_client = MLServiceClient()
