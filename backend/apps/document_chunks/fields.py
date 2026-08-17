"""
Vector field that is a real pgvector column on Postgres and a JSON-serialized
text column on SQLite.

Postgres is the production database and uses pgvector's ``vector(1024)`` type
with the ``<=>`` (cosine) operator and HNSW index for ANN search. The test
suite runs on SQLite, which has no vector type, so on SQLite the same field
stores a JSON array of floats and the retriever falls back to in-process numpy
cosine similarity. This keeps the entire test/CI story on SQLite while
production gets real pgvector.
"""

from __future__ import annotations

import json

from pgvector.django import VectorField


class EmbeddingVectorField(VectorField):
    """pgvector ``vector(dimensions)`` on Postgres, JSON text on SQLite."""

    def db_type(self, connection):
        if connection.vendor == "postgresql":
            return super().db_type(connection)
        return "TEXT"

    def deconstruct(self):
        name, _path, args, kwargs = super().deconstruct()
        return name, "apps.document_chunks.fields.EmbeddingVectorField", args, kwargs

    def get_db_prep_value(self, value, connection, prepared=False):
        if connection.vendor == "postgresql":
            return super().get_db_prep_value(value, connection, prepared)
        if value is None:
            return None
        if isinstance(value, str):
            return value
        if hasattr(value, "tolist"):
            value = value.tolist()
        return json.dumps(list(value))

    def from_db_value(self, value, expression, connection):
        if connection.vendor != "postgresql" and isinstance(value, str):
            try:
                return json.loads(value)
            except (TypeError, ValueError):
                return None
        return super().from_db_value(value, expression, connection)
