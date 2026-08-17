"""
Tests for the modular RAG pipeline: retriever (in-process fallback on SQLite),
source modules, orchestration service metrics, and the HTTP endpoint.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.data_streams.models import DataStream
from apps.document_chunks.models import DocumentChunk
from apps.document_chunks.services.rag.modules import modules_for_sources
from apps.document_chunks.services.rag.service import query_rag
from apps.document_chunks.services.rag.retriever import retrieve
from apps.users.models import User


def _make_user(email="rag-user@example.com", username="rag-user"):
    return User.objects.create_user(email=email, username=username, password="xpass12345!")


@contextmanager
def _capture_logger(name: str, level=logging.INFO):
    """Capture records on a specific logger, bypassing root propagation
    (the ``apps`` logger intentionally sets ``propagate: False``)."""
    logger = logging.getLogger(name)
    records: list[logging.LogRecord] = []
    handler = logging.Handler()
    handler.setLevel(level)
    handler.emit = records.append
    logger.addHandler(handler)
    try:
        yield records
    finally:
        logger.removeHandler(handler)


def _make_stream(user, source_type="email"):
    return DataStream.objects.create(
        user=user, source_type=source_type, payload={"source": source_type}
    )


def _make_chunk(user, content, embedding, source_type="email", category="general", metadata=None):
    stream = _make_stream(user, source_type)
    return DocumentChunk.objects.create(
        stream=stream,
        content=content,
        cluster_category=category,
        metadata=metadata or {},
        embedding=embedding,
    )


def _unit_vector(positions, dims=1024):
    vec = [0.0] * dims
    for pos in positions:
        vec[pos] = 1.0
    return vec


@pytest.mark.django_db
class TestRetrievePythonBackend:
    def test_ranks_most_similar_first(self):
        user = _make_user()
        _make_chunk(user, "unrelated content", _unit_vector([2]), category="general")
        _make_chunk(user, "target content", _unit_vector([0]), category="general")

        query_vec = _unit_vector([0])
        with patch(
            "apps.document_chunks.services.embedding_generation._generate_embedding_sync",
            return_value=query_vec,
        ):
            hits, backend = retrieve(user, "target content", min_score=0.0)

        assert backend in {"python", "pgvector"}
        assert [h["content"] for h in hits] == ["target content", "unrelated content"]
        assert hits[0]["score"] > hits[1]["score"]

    def test_respects_category_filter(self):
        user = _make_user()
        _make_chunk(user, "target content", _unit_vector([0]), category="job_alert")
        _make_chunk(user, "target content", _unit_vector([0]), category="receipt")

        query_vec = _unit_vector([0])
        with patch(
            "apps.document_chunks.services.embedding_generation._generate_embedding_sync",
            return_value=query_vec,
        ):
            hits, backend = retrieve(
                user, "target content", categories=["receipt"], min_score=0.3
            )

        assert backend in {"python", "pgvector"}
        assert len(hits) == 1
        assert hits[0]["category"] == "receipt"

    def test_high_threshold_falls_back_to_keyword(self):
        user = _make_user()
        _make_chunk(user, "far content", _unit_vector([9]), category="general")

        query_vec = _unit_vector([0])
        with patch(
            "apps.document_chunks.services.embedding_generation._generate_embedding_sync",
            return_value=query_vec,
        ):
            hits, backend = retrieve(user, "far content", min_score=0.9)

        # Vector search rejects the weak match, so the hybrid pipeline falls
        # back to keyword search, which still finds it by token overlap.
        assert backend == "keyword"
        assert [h["content"] for h in hits] == ["far content"]

    def test_no_match_returns_empty(self):
        user = _make_user()
        _make_chunk(user, "far content", _unit_vector([9]), category="general")

        query_vec = _unit_vector([0])
        with patch(
            "apps.document_chunks.services.embedding_generation._generate_embedding_sync",
            return_value=query_vec,
        ):
            hits, _backend = retrieve(user, "zzqqxx nonmatch", limit=5)

        assert hits == []

    def test_limit_is_clamped(self):
        user = _make_user()
        for i in range(5):
            _make_chunk(user, f"target content {i}", _unit_vector([0]), category="general")

        query_vec = _unit_vector([0])
        with patch(
            "apps.document_chunks.services.embedding_generation._generate_embedding_sync",
            return_value=query_vec,
        ):
            hits, _backend = retrieve(user, "target content", min_score=0.0, limit=2)

        assert len(hits) == 2


@pytest.mark.django_db
class TestRetrieveKeywordFallback:
    def test_keyword_fallback_on_zero_query_embedding(self):
        user = _make_user()
        _make_chunk(user, "Invoice #123 from Acme for services", _unit_vector([0]))
        _make_chunk(user, "Weekend plans with friends", _unit_vector([2]))

        with patch(
            "apps.document_chunks.services.embedding_generation._generate_embedding_sync",
            return_value=[0.0] * 1024,
        ):
            hits, backend = retrieve(user, "invoice payment", limit=5)

        assert backend == "keyword"
        assert any("Invoice" in h["content"] for h in hits)


@pytest.mark.django_db
class TestSourceModules:
    def test_email_module_annotates_and_boosts_confidence(self):
        user = _make_user()
        metadata = {"message_id": "<m@example.com>", "subject": "S", "sender": "x", "confidence": 0.9}
        _make_chunk(
            user,
            "Email body about the offer",
            _unit_vector([0]),
            source_type="email",
            category="job_offer",
            metadata=metadata,
        )

        query_vec = _unit_vector([0])
        with patch(
            "apps.document_chunks.services.embedding_generation._generate_embedding_sync",
            return_value=query_vec,
        ):
            payload = query_rag(user, "job offer", limit=3, min_score=0.0)

        assert payload["backend"] in {"python", "pgvector"}
        result = payload["results"][0]
        assert result["module_context"]["thread"] == "<m@example.com>"
        assert result["module_context"]["category"] == "job_offer"
        assert result["score"] > 1.0 - 1e-3

    def test_modules_for_sources_filters(self):
        modules = modules_for_sources(["kijiji", "jira"])
        names = {m.name for m in modules}
        assert {"kijiji", "jira"}.issubset(names)
        assert "email" not in names

    def test_unknown_source_falls_back_to_all(self):
        modules = modules_for_sources(["made_up_source"])
        assert len(modules) == len(modules_for_sources(None))


@pytest.mark.django_db
class TestServiceMetrics:
    def test_emits_rag_query_metric(self):
        user = _make_user()
        _make_chunk(user, "Meeting agenda for project sync", _unit_vector([0]))

        query_vec = _unit_vector([0])
        with (
            patch(
                "apps.document_chunks.services.embedding_generation._generate_embedding_sync",
                return_value=query_vec,
            ),
            _capture_logger("apps.metrics", logging.INFO) as records,
        ):
            query_rag(user, "meeting sync", limit=3, min_score=0.0)

        rag_events = [r for r in records if r.getMessage() == "rag_query"]
        assert rag_events, "expected a rag_query metric event"
        metrics = rag_events[0].metrics
        assert metrics["backend"] in {"python", "pgvector"}
        assert metrics["results"] >= 1
        assert "latency_ms" in metrics
        assert "source_distribution" in metrics
        assert metrics["answer_generated"] is False


@pytest.mark.django_db
class TestRagAPI:
    def _auth_client(self, user):
        client = APIClient()
        refresh = RefreshToken.for_user(user)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        return client

    def test_rag_query_endpoint(self):
        user = _make_user()
        _make_chunk(user, "Project proposal for the RAG feature", _unit_vector([0]))

        query_vec = _unit_vector([0])
        with patch(
            "apps.document_chunks.services.embedding_generation._generate_embedding_sync",
            return_value=query_vec,
        ):
            resp = self._auth_client(user).post(
                "/api/document-chunks/rag/query",
                {"query": "project proposal", "limit": 3, "min_score": 0.0},
                format="json",
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["backend"] in {"python", "pgvector"}
        assert len(data["results"]) == 1
        assert data["results"][0]["content"] == "Project proposal for the RAG feature"
        assert data["results"][0]["category"] == "general"
        assert data["source_distribution"] == {"email": 1}

    def test_rag_query_scoped_to_user(self):
        user_a = _make_user(email="a@example.com", username="user-a")
        user_b = _make_user(email="b@example.com", username="user-b")
        _make_chunk(user_a, "Secret content for A", _unit_vector([0]))
        _make_chunk(user_b, "Secret content for B", _unit_vector([0]))

        query_vec = _unit_vector([0])
        with patch(
            "apps.document_chunks.services.embedding_generation._generate_embedding_sync",
            return_value=query_vec,
        ):
            resp = self._auth_client(user_a).post(
                "/api/document-chunks/rag/query",
                {"query": "secret", "limit": 10, "min_score": 0.0},
                format="json",
            )

        assert resp.status_code == 200
        contents = [r["content"] for r in resp.json()["results"]]
        assert contents == ["Secret content for A"]

    def test_rag_query_requires_auth(self):
        resp = APIClient().post(
            "/api/document-chunks/rag/query",
            {"query": "anything"},
            format="json",
        )
        assert resp.status_code in (401, 403)
