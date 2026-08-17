import uuid

from django.conf import settings
from django.db import models


class DataStream(models.Model):
    """
    Data stream model for ingesting data from various sources.
    Supports Gmail, Kijiji, Plaid, Google Calendar.
    """

    SOURCE_TYPES = [
        ("gmail", "Gmail"),
        ("kijiji", "Kijiji"),
        ("plaid", "Plaid"),
        ("google_calendar", "Google Calendar"),
        ("manual", "Manual Entry"),
        ("jira", "Jira"),
        ("email", "Email (IMAP)"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="data_streams",
    )
    source_type = models.CharField(max_length=50, choices=SOURCE_TYPES)
    payload = models.JSONField()
    raw_data = models.JSONField(blank=True, null=True)
    processed_at = models.DateTimeField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("processing", "Processing"),
            ("completed", "Completed"),
            ("failed", "Failed"),
        ],
        default="pending",
    )
    error_message = models.TextField(blank=True, null=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "data_streams"
        verbose_name = "data stream"
        verbose_name_plural = "data streams"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.source_type} - {self.user.email}"
