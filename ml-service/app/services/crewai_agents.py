"""
CrewAI agents for ML-Auditor.
Email Clustering, Financial Audit, and Kijiji Negotiation agents.
"""

try:
    from crewai import Agent
    HAS_CREWAI = True
except ImportError:
    HAS_CREWAI = False

from app.services.nim_service import nim_service
import structlog

logger = structlog.get_logger()


class EmailClusteringAgent:
    """
    Agent for classifying and clustering emails.
    Categories: recrutement, urgent, finance, kijiji_deal, general
    """

    def __init__(self):
        self.agent = None
        if HAS_CREWAI:
            self.agent = Agent(
                role="Email Classifier",
                goal="Classify emails into appropriate categories and extract key information",
                backstory="""You are an expert email analyst who can quickly categorize emails
                and extract important entities like sender, dates, amounts, and action items.""",
                verbose=True,
                allow_delegation=False,
            )

    async def classify_email(self, email_content: str, subject: str = "", sender: str = "") -> dict:
        """
        Classify an email and extract entities.

        Args:
            email_content: Email body content
            subject: Email subject
            sender: Email sender

        Returns:
            Classification result with category and entities
        """
        categories = ["recrutement", "urgent", "finance", "kijiji_deal", "general"]

        # Classify email
        classification = await nim_service.classify_text(
            text=f"Subject: {subject}\nFrom: {sender}\n\n{email_content}",
            categories=categories,
        )

        # Extract entities
        entities = await nim_service.extract_entities(
            text=f"Subject: {subject}\nFrom: {sender}\n\n{email_content}",
            entity_types=["person", "organization", "date", "amount", "email", "phone"],
        )

        return {
            "category": classification.get("category", "general"),
            "confidence": classification.get("confidence", 0.0),
            "reasoning": classification.get("reasoning", ""),
            "entities": entities,
            "subject": subject,
            "sender": sender,
        }


class FinancialAuditAgent:
    """
    Agent for detecting financial anomalies using Isolation Forest.
    """

    def __init__(self):
        self.agent = None
        if HAS_CREWAI:
            self.agent = Agent(
                role="Financial Analyst",
                goal="Detect anomalies in financial transactions and provide insights",
                backstory="""You are a financial analyst expert who can identify unusual
                patterns, suspicious transactions, and potential fraud in banking data.""",
                verbose=True,
                allow_delegation=False,
            )

    async def detect_anomalies(self, transactions: list) -> dict:
        """
        Detect anomalies in transactions using Isolation Forest.

        Args:
            transactions: List of transaction dicts

        Returns:
            Anomaly detection results
        """
        if not transactions:
            return {"anomalies": [], "summary": "No transactions to analyze"}

        # TODO: Implement actual Isolation Forest
        # For now, return placeholder
        return {
            "anomalies": [],
            "summary": f"Analyzed {len(transactions)} transactions",
            "recommendations": [],
        }

    async def analyze_correlations(self, transactions: list) -> dict:
        """
        Analyze Pearson correlations between transactions.

        Args:
            transactions: List of transaction dicts

        Returns:
            Correlation analysis results
        """
        # TODO: Implement Pearson correlation analysis
        return {
            "correlations": [],
            "duplicates": [],
            "subscriptions": [],
        }


class KijijiNegotiationAgent:
    """
    Agent for analyzing Kijiji messages and suggesting negotiations.
    """

    def __init__(self):
        self.agent = None
        if HAS_CREWAI:
            self.agent = Agent(
                role="Negotiation Specialist",
                goal="Analyze marketplace messages and suggest optimal negotiation strategies",
                backstory="""You are an expert negotiator who can analyze messages, detect
                spam, identify genuine offers, and suggest counter-offers.""",
                verbose=True,
                allow_delegation=False,
            )

    async def analyze_message(self, message: str, listing_price: float = 0) -> dict:
        """
        Analyze a Kijiji message for spam/negotiation.

        Args:
            message: Message content
            listing_price: Original listing price

        Returns:
            Analysis results with recommendations
        """
        system_prompt = """You are a marketplace message analyzer. Analyze the message and provide:
1. Is it spam? (true/false)
2. Is it a genuine inquiry? (true/false)
3. Is it a lowball offer? (true/false)
4. Sentiment (positive/neutral/negative)
5. Suggested response (if applicable)

Return as JSON with keys: is_spam, is_genuine, is_lowball, sentiment, suggested_response, offer_amount (if mentioned)."""

        result = await nim_service.classify_text(
            text=message,
            categories=["spam", "genuine", "lowball", "serious_buyer"],
            system_prompt=system_prompt,
        )

        return {
            "is_spam": result.get("category") == "spam",
            "is_genuine": result.get("category") in ["genuine", "serious_buyer"],
            "is_lowball": result.get("category") == "lowball",
            "confidence": result.get("confidence", 0.0),
            "suggested_response": None,
            "listing_price": listing_price,
        }


# Singleton instances
email_agent = EmailClusteringAgent()
financial_agent = FinancialAuditAgent()
kijiji_agent = KijijiNegotiationAgent()
