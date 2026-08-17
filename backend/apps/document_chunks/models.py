import uuid

from django.db import models

from .fields import EmbeddingVectorField


class DocumentChunk(models.Model):
    """
    Document chunk model for RAG memory.
    Stores embeddings for semantic search using pgvector.
    """

    CLUSTER_CATEGORIES = [
        ("recrutement", "Recrutement"),
        ("urgent", "Urgent"),
        ("finance", "Finance"),
        ("kijiji_deal", "Kijiji Deal"),
        ("calendar", "Calendar"),
        ("general", "General"),
        ("jira", "Jira"),
        ("social", "Social"),
        ("job_alert", "Job Alert"),
        ("job_event", "Job Event"),
        ("networking", "Networking"),
        ("receipt", "Receipt"),
        ("security", "Security"),
        ("newsletter", "Newsletter"),
        ("project_idea", "Project Idea"),
        ("job_offer", "Job Offer"),
        ("job_rejection", "Job Rejection"),
        ("job_interview", "Job Interview"),
        ("subscription", "Subscription"),
        ("shipping", "Shipping"),
        ("marketing", "Marketing"),
        ("survey", "Survey"),
        ("travel", "Travel"),
        ("meeting", "Meeting"),
        ("legal", "Legal"),
        ("document", "Document"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stream = models.ForeignKey(
        "data_streams.DataStream",
        on_delete=models.CASCADE,
        related_name="document_chunks",
    )
    content = models.TextField()
    embedding = EmbeddingVectorField(
        dimensions=1024,
        null=True,
        blank=True,
        help_text="pgvector embedding for semantic search (1024 dimensions)",
    )
    cluster_category = models.CharField(
        max_length=100,
        choices=CLUSTER_CATEGORIES,
        default="general",
    )
    metadata = models.JSONField(blank=True, null=True)

    # Chunking metadata
    chunk_index = models.IntegerField(default=0)
    total_chunks = models.IntegerField(default=1)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "document_chunks"
        verbose_name = "document chunk"
        verbose_name_plural = "document chunks"
        indexes = [
            models.Index(fields=["cluster_category"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"Chunk {self.chunk_index}/{self.total_chunks} - {self.cluster_category}"
