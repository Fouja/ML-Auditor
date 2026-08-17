"""Mock data generator for ML-Auditor.

Activating mock data injects realistic placeholder content into the same
pipelines used by real integrations so every surface (clusters, alerts,
analytics, chatbot RAG) has something to show:

- ``DataStream`` rows tagged ``{"mock": True}`` (source types gmail/plaid)
- ``DocumentChunk`` rows with cluster categories + embeddings (RAG/clusters)
- ``AgentAlert`` rows tagged source_type "mock" (notifications/alerts feed)

Deactivating removes exactly those rows, leaving real data untouched.
"""

import logging

from django.utils import timezone

logger = logging.getLogger(__name__)

MOCK_MARKER = "mock"

EMAIL_CHUNKS = [
    {
        "content": (
            "Job alert: Senior ML Engineer position at ScaleWorks posted today. "
            "Remote friendly, salary range $160k-$190k, requires 5+ years of "
            "production machine learning experience and strong Python."
        ),
        "cluster_category": "job_alert",
        "subject": "New job alert: Senior ML Engineer at ScaleWorks",
        "sender": "job-alerts@scaleworks.com",
        "date": "2026-08-10 09:14",
    },
    {
        "content": (
            "Job offer: Congrats! DataNova would like to extend an offer for the "
            "Data Scientist role. Start date flexible, offer expires in 7 days. "
            "Reply to accept the offer."
        ),
        "cluster_category": "job_offer",
        "subject": "Offer: Data Scientist at DataNova",
        "sender": "recruiting@datanova.io",
        "date": "2026-08-09 16:40",
    },
    {
        "content": (
            "Interview scheduled: Technical interview with CloudMatrix for the "
            "Backend Engineer position on Friday at 2:00 PM. Prepare for system "
            "design and a live coding round in Python."
        ),
        "cluster_category": "job_interview",
        "subject": "Interview confirmed: CloudMatrix — Backend Engineer",
        "sender": "talent@cloudmatrix.dev",
        "date": "2026-08-08 11:05",
    },
    {
        "content": (
            "Rejection notice: Thank you for applying to FinLoop, however we have "
            "decided to move forward with other candidates. Keep in touch for "
            "future opportunities."
        ),
        "cluster_category": "job_rejection",
        "subject": "Update on your application at FinLoop",
        "sender": "careers@finloop.com",
        "date": "2026-08-07 13:22",
    },
    {
        "content": (
            "Invoice #INV-2041 from CloudHost Ltd: $124.50 for hosting services "
            "for the month. Due on the 15th. Pay via the portal or bank transfer."
        ),
        "cluster_category": "receipt",
        "subject": "Invoice #INV-2041 from CloudHost Ltd",
        "sender": "billing@cloudhost.ltd",
        "date": "2026-08-06 08:30",
    },
    {
        "content": (
            "Security alert: New sign-in to your account from an unrecognized "
            "device in Montreal, Quebec. If this was you, no action needed. "
            "Otherwise, reset your password immediately."
        ),
        "cluster_category": "security",
        "subject": "Security alert: new sign-in detected",
        "sender": "security@mlauditor.app",
        "date": "2026-08-10 03:12",
    },
    {
        "content": (
            "Newsletter: AI Weekly #128 — this week: local LLM frameworks, "
            "vector databases at scale, and a hands-on guide to building RAG "
            "pipelines with pgvector."
        ),
        "cluster_category": "newsletter",
        "subject": "AI Weekly #128 — local LLMs and pgvector RAG",
        "sender": "newsletter@aiweekly.dev",
        "date": "2026-08-08 07:00",
    },
    {
        "content": (
            "Recruitment update: 12 candidates applied for the Product Manager "
            "role this week. 4 moved to the interview stage, 2 received offers, "
            "1 accepted."
        ),
        "cluster_category": "recrutement",
        "subject": "Weekly recruitment update — Product Manager",
        "sender": "hr@mlauditor.app",
        "date": "2026-08-09 17:45",
    },
    {
        "content": (
            "URGENT: Production incident in the checkout service. Error rates "
            "above 8% for the last 30 minutes. On-call engineer paged, incident "
            "ticket INC-4421 opened."
        ),
        "cluster_category": "urgent",
        "subject": "URGENT — P1 incident in checkout service",
        "sender": "oncall@ops.mlauditor.app",
        "date": "2026-08-11 06:20",
    },
    {
        "content": (
            "Marketing report: this month's email campaign reached 28,000 "
            "subscribers with a 4.2% click-through rate. Landing page conversion "
            "improved to 6.1% after the redesign."
        ),
        "cluster_category": "marketing",
        "subject": "Monthly campaign report — August",
        "sender": "growth@mlauditor.app",
        "date": "2026-08-10 15:30",
    },
]

PLAID_CHUNKS = [
    {
        "content": (
            "Transaction: TORONTO TRANSIT COMMISSION - Toronto, $6.75. "
            "Transportation expense, commuter monthly budget tracked as travel."
        ),
        "cluster_category": "travel",
    },
    {
        "content": (
            "Transaction: NETFLIX.COM - $17.99. Recurring streaming subscription "
            "charged monthly."
        ),
        "cluster_category": "subscription",
    },
    {
        "content": (
            "Transaction: AMAZON.CA - $89.34. Online shopping purchase, electronics."
        ),
        "cluster_category": "receipt",
    },
    {
        "content": (
            "Transaction: GROCERY DEPOT - $142.08. Weekly groceries, household "
            "spending category."
        ),
        "cluster_category": "receipt",
    },
    {
        "content": (
            "Transaction: PAYCHECK - $3,250.00 direct deposit from employer, "
            "biweekly salary."
        ),
        "cluster_category": "finance",
    },
    {
        "content": (
            "Transaction: RENT - $1,850.00 monthly rent payment to landlord."
        ),
        "cluster_category": "finance",
    },
    {
        "content": (
            "Transaction: GYM MEMBERSHIP - $39.99. Monthly fitness subscription."
        ),
        "cluster_category": "subscription",
    },
    {
        "content": (
            "Transaction: AIR CANADA - $412.60. Flight booking for upcoming "
            "business trip, travel expense."
        ),
        "cluster_category": "travel",
    },
]

ALERTS = [
    {
        "title": "New job matches found",
        "description": (
            "Argus found 3 new job postings matching your profile: Senior ML "
            "Engineer at ScaleWorks, Data Scientist at DataNova, Backend Engineer "
            "at CloudMatrix."
        ),
        "severity": "medium",
    },
    {
        "title": "Interview scheduled for Friday",
        "description": (
            "Technical interview with CloudMatrix is confirmed for Friday at 2:00 "
            "PM. Suggested preparation: review system design fundamentals."
        ),
        "severity": "high",
    },
    {
        "title": "Security: unrecognized sign-in",
        "description": (
            "A new sign-in from Montreal, QC was detected on your account. "
            "Review recent activity and change your password if needed."
        ),
        "severity": "critical",
    },
    {
        "title": "Monthly budget check",
        "description": (
            "Spending this month is tracking 8% above your usual pace, driven by "
            "travel expenses. Consider reviewing the travel budget line."
        ),
        "severity": "low",
    },
    {
        "title": "Job offer waiting for reply",
        "description": (
            "DataNova's offer for the Data Scientist role expires in 7 days. "
            "Ready to accept or negotiate terms."
        ),
        "severity": "high",
    },
    {
        "title": "Invoice due this week",
        "description": (
            "Invoice INV-2041 ($124.50) from CloudHost Ltd is due on the 15th. "
            "An automated reminder was generated."
        ),
        "severity": "medium",
    },
]


def _build_stream(user, source_type: str, label: str):
    from apps.data_streams.models import DataStream

    return DataStream.objects.create(
        user=user,
        source_type=source_type,
        payload={"mock": True, "label": label},
        raw_data={"mock": True, "label": label, "source": "mock_data_service"},
        status="completed",
        processed_at=timezone.now(),
    )


def _embed(content: str):
    try:
        from apps.document_chunks.services.embedding_generation import _generate_embedding_sync

        return _generate_embedding_sync(content)
    except Exception:
        return None


def activate_mock_data(user) -> dict:
    """Inject mock streams, chunks and alerts for the user."""
    from apps.alerts.models import AgentAlert
    from apps.document_chunks.models import DocumentChunk
    from apps.data_streams.models import DataStream

    if user.mock_data_enabled:
        return mock_data_status(user)

    email_stream = _build_stream(user, "gmail", "Mock Gmail feed")
    plaid_stream = _build_stream(user, "plaid", "Mock Plaid feed")

    chunk_count = 0
    for item in EMAIL_CHUNKS:
        DocumentChunk.objects.create(
            stream=email_stream,
            content=item["content"],
            cluster_category=item["cluster_category"],
            metadata={
                "mock": True,
                "subject": item.get("subject", ""),
                "sender": item.get("sender", ""),
                "date": item.get("date", ""),
            },
            embedding=_embed(item["content"]),
        )
        chunk_count += 1
    for item in PLAID_CHUNKS:
        DocumentChunk.objects.create(
            stream=plaid_stream,
            content=item["content"],
            cluster_category=item["cluster_category"],
            metadata={"mock": True},
            embedding=_embed(item["content"]),
        )
        chunk_count += 1

    alert_count = 0
    for item in ALERTS:
        AgentAlert.objects.create(
            user=user,
            title=item["title"],
            description=item["description"],
            severity=item["severity"],
            source_type=MOCK_MARKER,
            action_payload={"mock": True},
        )
        alert_count += 1

    user.mock_data_enabled = True
    user.save(update_fields=["mock_data_enabled"])

    return {
        "enabled": True,
        "chunks_created": chunk_count,
        "alerts_created": alert_count,
        "streams_created": 2,
    }


def deactivate_mock_data(user) -> dict:
    """Remove mock streams, chunks and alerts, leaving real data intact."""
    from apps.alerts.models import AgentAlert
    from apps.data_streams.models import DataStream

    deleted_streams = 0
    for stream in DataStream.objects.filter(user=user, payload__mock=True):
        stream.delete()
        deleted_streams += 1

    deleted_alerts = AgentAlert.objects.filter(
        user=user, source_type=MOCK_MARKER
    ).delete()[0]

    user.mock_data_enabled = False
    user.save(update_fields=["mock_data_enabled"])

    return {
        "enabled": False,
        "streams_deleted": deleted_streams,
        "alerts_deleted": deleted_alerts,
    }


def mock_data_status(user) -> dict:
    from apps.alerts.models import AgentAlert
    from apps.document_chunks.models import DocumentChunk
    from apps.data_streams.models import DataStream

    streams = DataStream.objects.filter(user=user, payload__mock=True)
    chunks = DocumentChunk.objects.filter(stream__in=streams).count()
    alerts = AgentAlert.objects.filter(user=user, source_type=MOCK_MARKER).count()
    return {
        "enabled": bool(user.mock_data_enabled),
        "streams": streams.count(),
        "chunks": chunks,
        "alerts": alerts,
    }
