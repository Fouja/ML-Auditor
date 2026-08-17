"""
Integration tests for the real pgvector code path.

These only run when the suite is pointed at Postgres via
``DJANGO_TEST_DATABASE_URL`` (e.g. ``postgres://mlauditor:mlauditor@db:5432/mlauditor_db``),
because SQLite has no vector type and cannot execute ``<=>``. Running them
proves the ``CosineDistance`` annotation, the ``<=>`` operator and the
vector-column round-trip (write list -> read vector) all work end to end.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from apps.data_streams.models import DataStream
from apps.document_chunks.models import DocumentChunk
from apps.document_chunks.services.rag.service import query_rag
from apps.document_chunks.services.rag.retriever import retrieve
from apps.users.models import User

pytestmark = pytest.mark.skipif(
    not os.environ.get("DJANGO_TEST_DATABASE_URL"),
    reason="requires Postgres (set DJANGO_TEST_DATABASE_URL)",
)


def _unit_vector(positions, dims=1024):
    vec = [0.0] * dims
    for pos in positions:
        vec[pos] = 1.0
    return vec


@pytest.mark.django_db
class TestPgvectorRetrieval:
    def test_column_is_real_vector_type(self):
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT udt_name FROM information_schema.columns "
                "WHERE table_name='document_chunks' AND column_name='embedding'"
            )
            udt = cursor.fetchone()[0]
        assert udt == "vector"

    def test_hnsw_index_exists(self):
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT indexdef FROM pg_indexes "
                "WHERE tablename='document_chunks' AND indexname='document_chunks_embedding_idx'"
            )
            row = cursor.fetchone()
        assert row is not None
        assert "hnsw" in row[0]

    def test_pgvector_ranking_via_cosine_operator(self):
        user = User.objects.create_user(
            email="pgvec@example.com", username="pgvec", password="xpass12345!"
        )
        stream = DataStream.objects.create(
            user=user, source_type="email", payload={"source": "email"}
        )
        DocumentChunk.objects.create(
            stream=stream,
            content="close match content",
            cluster_category="general",
            metadata={},
            embedding=_unit_vector([0]),
        )
        DocumentChunk.objects.create(
            stream=stream,
            content="far away content",
            cluster_category="general",
            metadata={},
            embedding=_unit_vector([5]),
        )

        query_vec = _unit_vector([0])
        with patch(
            "apps.document_chunks.services.embedding_generation._generate_embedding_sync",
            return_value=query_vec,
        ):
            hits, backend = retrieve(user, "close match", min_score=0.3)

        assert backend == "pgvector"
        assert [h["content"] for h in hits] == ["close match content"]
        assert hits[0]["score"] > 0.9

    def test_pgvector_service_end_to_end(self):
        user = User.objects.create_user(
            email="pgvec-svc@example.com", username="pgvec-svc", password="xpass12345!"
        )
        stream = DataStream.objects.create(
            user=user, source_type="email", payload={"source": "email"}
        )
        DocumentChunk.objects.create(
            stream=stream,
            content="Invoice for the design sprint",
            cluster_category="receipt",
            metadata={"confidence": 0.8},
            embedding=_unit_vector([0]),
        )

        query_vec = _unit_vector([0])
        with patch(
            "apps.document_chunks.services.embedding_generation._generate_embedding_sync",
            return_value=query_vec,
        ):
            payload = query_rag(user, "invoice", limit=3, min_score=0.0)

        assert payload["backend"] == "pgvector"
        assert len(payload["results"]) == 1
        assert payload["results"][0]["category"] == "receipt"
        assert payload["source_distribution"] == {"email": 1}

    def test_embedding_round_trip_write_and_read(self):
        user = User.objects.create_user(
            email="pgvec-rt@example.com", username="pgvec-rt", password="xpass12345!"
        )
        stream = DataStream.objects.create(
            user=user, source_type="email", payload={"source": "email"}
        )
        vec = _unit_vector([3, 9])
        chunk = DocumentChunk.objects.create(
            stream=stream,
            content="round trip",
            cluster_category="general",
            metadata={},
            embedding=vec,
        )
        chunk.refresh_from_db()
        stored = list(chunk.embedding)
        assert len(stored) == 1024
        assert stored[3] == 1.0
        assert stored[9] == 1.0
        assert stored[0] == 0.0
