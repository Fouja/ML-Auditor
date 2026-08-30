"""
Models for tracking integration sync state.
"""

import uuid

from django.conf import settings
from django.db import models

from config.security import decrypt_secret, encrypt_secret, is_encrypted


class IntegrationConnection(models.Model):
    """Tracks an external service connection for a user.

    A user may have multiple connections for the same service (e.g. several
    Gmail accounts or several bank accounts). Tokens are stored here instead
    of on the User model so each account can be synced independently.
    """

    SERVICE_CHOICES = [
        ("gmail", "Gmail"),
        ("google_calendar", "Google Calendar"),
        ("plaid", "Plaid (Banking)"),
        ("kijiji", "Kijiji"),
        ("jira", "Jira"),
        ("email", "Email (IMAP)"),
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
    account_label = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Human-readable label for this account (e.g. email address or bank name).",
    )
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="active")
    is_active = models.BooleanField(default=True)
    access_token = models.TextField(blank=True, default="")
    refresh_token = models.TextField(blank=True, default="")
    extra_data = models.JSONField(blank=True, default=dict)
    last_synced = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True, default="")
    items_synced = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "service", "account_label")
        ordering = ["-updated_at"]

    def __str__(self):
        label = self.account_label or self.get_service_display()
        return f"{self.user} — {label} ({self.status})"


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


class ApiKeyIntegration(models.Model):
    """User-managed API key credentials for external integrations.

    Unlike OAuth-based IntegrationConnection records, these are manually
    entered API keys / secrets / tokens that the user can add, edit, delete,
    and test from the Integrations dashboard.
    """

    SERVICE_CHOICES = [
        ("plaid", "Plaid"),
        ("gmail", "Gmail / Google API"),
        ("google_calendar", "Google Calendar"),
        ("canva", "Canva"),
        ("jira", "Jira"),
        ("openai", "OpenAI"),
        ("anthropic", "Anthropic"),
        ("nvidia", "NVIDIA NIM"),
        ("custom", "Custom API"),
    ]
    STATUS_CHOICES = [
        ("unknown", "Unknown"),
        ("active", "Active"),
        ("error", "Error"),
        ("disabled", "Disabled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="api_key_integrations",
    )
    service = models.CharField(max_length=32, choices=SERVICE_CHOICES)
    label = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Human-readable label for this API key set.",
    )
    api_key = models.TextField(blank=True, default="")
    api_secret = models.TextField(blank=True, default="")
    extra_data = models.JSONField(blank=True, default=dict)
    is_active = models.BooleanField(default=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="unknown")
    last_tested = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def save(self, *args, **kwargs):
        if self.api_key and not is_encrypted(self.api_key):
            self.api_key = encrypt_secret(self.api_key)
        if self.api_secret and not is_encrypted(self.api_secret):
            self.api_secret = encrypt_secret(self.api_secret)
        super().save(*args, **kwargs)

    @property
    def decrypted_api_key(self) -> str:
        return decrypt_secret(self.api_key) if self.api_key else ""

    @property
    def decrypted_api_secret(self) -> str:
        return decrypt_secret(self.api_secret) if self.api_secret else ""

    def __str__(self):
        label = self.label or self.get_service_display()
        return f"{self.user} — {label} ({self.status})"


class IntegrationLog(models.Model):
    """Generic state/event log for any integration (OAuth or API key)."""

    LEVEL_CHOICES = [
        ("info", "Info"),
        ("success", "Success"),
        ("warning", "Warning"),
        ("error", "Error"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="integration_logs",
    )
    service = models.CharField(max_length=32)
    connection = models.ForeignKey(
        IntegrationConnection,
        on_delete=models.CASCADE,
        related_name="integration_logs",
        null=True,
        blank=True,
    )
    api_key = models.ForeignKey(
        ApiKeyIntegration,
        on_delete=models.CASCADE,
        related_name="integration_logs",
        null=True,
        blank=True,
    )
    level = models.CharField(max_length=16, choices=LEVEL_CHOICES, default="info")
    message = models.TextField()
    metadata = models.JSONField(blank=True, default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.service} [{self.level}] {self.created_at}"


class LLMConfiguration(models.Model):
    """Configuration des LLMs disponibles pour chaque utilisateur"""

    LLM_PROVIDERS = [
        ("openai", "OpenAI (GPT-4, etc.)"),
        ("anthropic", "Anthropic (Claude)"),
        ("nvidia", "NVIDIA NIM"),
        ("ollama", "Ollama (Local)"),
        ("huggingface", "Hugging Face"),
        ("groq", "Groq (Free)"),
        ("openrouter", "OpenRouter (Free models)"),
        ("mistral", "Mistral AI"),
        ("gemini", "Google Gemini (Free)"),
        ("deepseek", "DeepSeek"),
        ("together", "Together AI"),
        ("lmstudio", "LM Studio (Local)"),
        ("custom", "Custom API"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="llm_configs"
    )
    provider = models.CharField(max_length=50, choices=LLM_PROVIDERS)
    name = models.CharField(max_length=255)
    api_key = models.CharField(max_length=1000)  # Encrypted at rest (enc::...)
    api_endpoint = models.URLField(blank=True, null=True)
    model_name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.api_key and not is_encrypted(self.api_key):
            self.api_key = encrypt_secret(self.api_key)
        super().save(*args, **kwargs)

    @property
    def decrypted_api_key(self) -> str:
        """Plaintext key for outbound API calls. Never serialize this."""
        return decrypt_secret(self.api_key)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("user", "provider", "model_name")

    def __str__(self):
        return f"{self.user.email} - {self.name}"
