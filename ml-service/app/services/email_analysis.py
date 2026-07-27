"""
Email analysis service for ML-Auditor.
Combines NIM classification with entity extraction.
"""

from typing import Optional
import structlog

from app.services.nim_service import nim_service
from app.services.crewai_agents import email_agent

logger = structlog.get_logger()


class EmailAnalysisService:
    """
    Service for comprehensive email analysis.
    """

    async def analyze_email(
        self,
        content: str,
        subject: str = "",
        sender: str = "",
        user_id: Optional[str] = None,
    ) -> dict:
        """
        Perform full email analysis.

        Args:
            content: Email body content
            subject: Email subject
            sender: Email sender
            user_id: Optional user ID for context

        Returns:
            Complete analysis result
        """
        logger.info(f"Analyzing email from {sender}")

        # Classify email
        classification = await email_agent.classify_email(
            email_content=content,
            subject=subject,
            sender=sender,
        )

        # Generate embedding for semantic search
        embedding = await nim_service.generate_embedding(
            f"Subject: {subject}\nFrom: {sender}\n\n{content}"
        )

        # Determine priority
        priority = self._determine_priority(classification)

        return {
            "category": classification["category"],
            "confidence": classification["confidence"],
            "reasoning": classification["reasoning"],
            "entities": classification["entities"],
            "priority": priority,
            "embedding": embedding,
            "metadata": {
                "subject": subject,
                "sender": sender,
                "user_id": user_id,
            },
        }

    def _determine_priority(self, classification: dict) -> str:
        """
        Determine email priority based on classification.

        Args:
            classification: Classification result

        Returns:
            Priority level: low, medium, high, critical
        """
        category = classification.get("category", "general")
        confidence = classification.get("confidence", 0.0)

        if category == "urgent" and confidence > 0.8:
            return "critical"
        elif category == "finance" and confidence > 0.7:
            return "high"
        elif category == "recrutement":
            return "medium"
        else:
            return "low"

    async def batch_analyze(
        self,
        emails: list[dict],
        user_id: Optional[str] = None,
    ) -> list[dict]:
        """
        Analyze multiple emails in batch.

        Args:
            emails: List of email dicts with content, subject, sender
            user_id: Optional user ID

        Returns:
            List of analysis results
        """
        results = []
        for email in emails:
            result = await self.analyze_email(
                content=email.get("content", ""),
                subject=email.get("subject", ""),
                sender=email.get("sender", ""),
                user_id=user_id,
            )
            results.append(result)

        return results


# Singleton instance
email_analysis_service = EmailAnalysisService()
