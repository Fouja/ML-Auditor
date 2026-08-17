"""
Tests for the email clustering service (heuristic classify + pgvector chunk
persistence with message-id dedup).
"""

from __future__ import annotations

from unittest.mock import patch

from apps.document_chunks.services.email_clustering import (
    classify_email,
    heuristic_classify,
    index_email_messages,
    persist_email_chunk,
)


class TestHeuristicClassify:
    def test_job_alert_subject(self):
        assert heuristic_classify("New job matches for you on Indeed") == "job_alert"

    def test_security_verification(self):
        assert heuristic_classify("Your verification code is 482910") == "security"

    def test_receipt_subject(self):
        assert heuristic_classify("Your receipt from Amazon") == "receipt"

    def test_networking(self):
        assert heuristic_classify("Invitation to connect on LinkedIn") == "networking"

    def test_newsletter(self):
        assert heuristic_classify("The Week in Tech — newsletter") == "newsletter"

    def test_social_platform(self):
        assert heuristic_classify("New follower on Instagram") == "social"

    def test_job_event(self):
        assert heuristic_classify("Career Fair: join us Thursday") == "job_event"

    def test_project_idea(self):
        assert heuristic_classify("Brainstorm: a side-project idea for you") == "project_idea"

    def test_urgent(self):
        assert heuristic_classify("URGENT: action required on your account") == "urgent"

    def test_general_fallback(self):
        assert heuristic_classify("Weekend plans") == "general"


class TestClassifyEmail:
    def test_refines_general_via_llm(self):
        with patch(
            "apps.document_chunks.services.email_clustering._llm_classify",
            return_value="job_alert",
        ):
            assert classify_email("Hello there") == "job_alert"

    def test_keeps_heuristic_hit_without_llm(self):
        with patch(
            "apps.document_chunks.services.email_clustering._llm_classify",
            return_value="",
        ) as llm:
            assert classify_email("New job alert: Senior Engineer at Acme") == "job_alert"
            llm.assert_not_called()

    def test_general_when_llm_fails(self):
        with patch(
            "apps.document_chunks.services.email_clustering._llm_classify",
            return_value="",
        ):
            assert classify_email("Something unrelated") == "general"


class TestPersistEmailChunk:
    def test_creates_chunk_and_dedups_by_message_id(self, db):
        from apps.data_streams.models import DataStream
        from apps.users.models import User

        user = User.objects.create_user(
            email="rag-test@example.com",
            username="rag-test",
            password="xpass12345!",
        )
        stream = DataStream.objects.create(
            user=user, source_type="email", payload={"source": "email"}
        )

        email = {
            "message_id": "<msg-1@example.com>",
            "subject": "New job matches for you",
            "from": "jobs@indeed.com",
            "body_text": "Here are 10 roles that match your profile.",
        }
        with patch(
            "apps.document_chunks.services.embedding_generation._generate_embedding_sync",
            return_value=[0.1] * 1024,
        ):
            first = persist_email_chunk(stream, email)
            second = persist_email_chunk(stream, email)

        assert first == {"created": True, "message_id": "<msg-1@example.com>"}
        assert second == {"created": False, "message_id": "<msg-1@example.com>"}

        from apps.document_chunks.models import DocumentChunk

        chunk = DocumentChunk.objects.get(stream=stream)
        assert chunk.cluster_category == "job_alert"
        assert chunk.metadata["message_id"] == "<msg-1@example.com>"
        assert DocumentChunk.objects.filter(stream=stream).count() == 1

    def test_index_email_messages_counts(self, db):
        from apps.data_streams.models import DataStream
        from apps.users.models import User

        user = User.objects.create_user(
            email="rag-index@example.com",
            username="rag-index",
            password="xpass12345!",
        )
        messages = [
            {
                "message_id": "<a@example.com>",
                "subject": "Your receipt from Amazon",
                "body_text": "Order confirmed.",
            },
            {
                "message_id": "<b@example.com>",
                "subject": "Personal note",
                "body_text": "How have you been?",
            },
        ]
        with patch(
            "apps.document_chunks.services.embedding_generation._generate_embedding_sync",
            return_value=[0.2] * 1024,
        ):
            summary = index_email_messages(user, messages, source_type="email")

        assert summary["created"] == 2
        assert summary["skipped"] == 0
        assert summary["total"] == 2
        assert DataStream.objects.filter(
            user=user, source_type="email"
        ).count() == 1
