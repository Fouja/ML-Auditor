"""
Models for tracking integration sync state.
"""

import uuid
from django.conf import settings
from django.db import models


class IntegrationConnection(models.Model):
    """Tracks an external service connection for a user."""

    SERVICE_CHOICES = [
        ("gmail", "Gmail"),
        ("google_calendar", "Google Calendar"),
        ("plaid", "Plaid (Banking)"),
        ("kijiji", "Kijiji"),
    ]
    STATUS_CHOICES = [
        ("active", "Active"),
        ("error", "Error"),
        ("expired", "Expired"),
        ("disconnected", "Disconnected"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="integration_connections",
    )
    service = models.CharField(max_length=32, choices=SERVICE_CHOICES)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="active")
    last_synced = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True, default="")
    items_synced = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "service")
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.user} — {self.get_service_display()} ({self.status})"


class SyncLog(models.Model):
    """Individual sync run log."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    connection = models.ForeignKey(
        IntegrationConnection,
        on_delete=models.CASCADE,
        related_name="sync_logs",
    )
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    success = models.BooleanField(default=True)
    items_synced = models.IntegerField(default=0)
    error_message = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        status = "OK" if self.success else "FAIL"
        return f"{self.connection} sync {status} @ {self.started_at}"


class LLMConfiguration(models.Model):
    """Configuration des LLMs disponibles pour chaque utilisateur"""
    
    LLM_PROVIDERS = [
        ('openai', 'OpenAI (GPT-4, etc.)'),
        ('anthropic', 'Anthropic (Claude)'),
        ('nvidia', 'NVIDIA NIM'),
        ('ollama', 'Ollama (Local)'),
        ('huggingface', 'Hugging Face'),
        ('custom', 'Custom API'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='llm_configs'
    )
    provider = models.CharField(max_length=50, choices=LLM_PROVIDERS)
    name = models.CharField(max_length=255)
    api_key = models.CharField(max_length=500)
    api_endpoint = models.URLField(blank=True, null=True)
    model_name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ('user', 'provider', 'model_name')
    
    def __str__(self):
        return f"{self.user.email} - {self.name}"
