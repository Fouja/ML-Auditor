"""
NVIDIA NIM (NVIDIA Inference Microservices) service.
Provides LLM and embedding capabilities.
"""

import os
from typing import List, Optional
from openai import AsyncOpenAI
import structlog

logger = structlog.get_logger()


class NIMService:
    """
    NVIDIA NIM service for LLM and embeddings.
    Uses OpenAI-compatible API.
    """

    def __init__(self):
        self.api_key = os.getenv("NIM_API_KEY", "dummy")
        self.base_url = os.getenv(
            "NIM_BASE_URL", "https://integrate.api.nvidia.com/v1"
        )
        self.model = os.getenv("NIM_MODEL", "meta/llama-3.3-70b-instruct")
        self.embedding_model = os.getenv(
            "NIM_EMBEDDING_MODEL", "nvidia/nv-embedqa-e5-v5"
        )
        self._client = None

    @property
    def client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
        return self._client

    async def chat_completion(
        self,
        messages: List[dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> str:
        """
        Generate chat completion using NIM.

        Args:
            messages: List of message dicts with role and content
            model: Model to use (defaults to configured model)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text
        """
        try:
            response = await self.client.chat.completions.create(
                model=model or self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"NIM chat completion error: {e}")
            raise

    async def classify_text(
        self,
        text: str,
        categories: List[str],
        system_prompt: Optional[str] = None,
    ) -> dict:
        """
        Classify text into categories using NIM.

        Args:
            text: Text to classify
            categories: List of possible categories
            system_prompt: Optional system prompt

        Returns:
            Dict with category and confidence
        """
        default_prompt = f"""You are a text classifier. Classify the following text into exactly one of these categories: {', '.join(categories)}.

Return your response as JSON with the following format:
{{"category": "category_name", "confidence": 0.0-1.0, "reasoning": "brief explanation"}}

Only return the JSON, no other text."""

        messages = [
            {"role": "system", "content": system_prompt or default_prompt},
            {"role": "user", "content": text},
        ]

        try:
            response = await self.chat_completion(messages, temperature=0.3)
            import json
            return json.loads(response)
        except Exception as e:
            logger.error(f"Classification error: {e}")
            return {"category": "unknown", "confidence": 0.0, "reasoning": str(e)}

    async def extract_entities(
        self,
        text: str,
        entity_types: Optional[List[str]] = None,
    ) -> List[dict]:
        """
        Extract entities from text using NIM.

        Args:
            text: Text to extract entities from
            entity_types: Types of entities to extract

        Returns:
            List of extracted entities
        """
        default_types = ["person", "organization", "date", "amount", "location", "email", "phone"]

        system_prompt = f"""You are an entity extraction system. Extract the following types of entities from the text: {', '.join(entity_types or default_types)}.

Return your response as JSON with the following format:
{{
  "entities": [
    {{"type": "entity_type", "value": "entity_value", "confidence": 0.0-1.0}}
  ]
}}

Only return the JSON, no other text."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ]

        try:
            response = await self.chat_completion(messages, temperature=0.2)
            import json
            result = json.loads(response)
            return result.get("entities", [])
        except Exception as e:
            logger.error(f"Entity extraction error: {e}")
            return []

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text using NIM.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        try:
            response = await self.client.embeddings.create(
                model=self.embedding_model,
                input=text,
            )
            return response.data[0].embedding
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
            response = await self.client.embeddings.create(
                model=self.embedding_model,
                input=texts,
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error(f"Batch embedding error: {e}")
            raise


# Singleton instance
nim_service = NIMService()
