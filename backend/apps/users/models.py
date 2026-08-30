import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom User model for ML-Auditor.
    Extends Django's AbstractUser with additional fields.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, max_length=255)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    avatar_url = models.URLField(blank=True, null=True)

    # OAuth tokens (encrypted in production)
    google_access_token = models.TextField(blank=True, null=True)
    google_refresh_token = models.TextField(blank=True, null=True)
    plaid_access_token = models.TextField(blank=True, null=True)
    canva_access_token = models.TextField(blank=True, null=True)
    canva_refresh_token = models.TextField(blank=True, null=True)

    # Jira (API token based)
    jira_api_token = models.TextField(blank=True, default="")
    jira_email = models.EmailField(blank=True, default="")
    jira_site_url = models.CharField(max_length=255, blank=True, default="")

    # Jira (OAuth 2.0)
    jira_oauth_access_token = models.TextField(blank=True, default="")
    jira_oauth_refresh_token = models.TextField(blank=True, default="")

    # IMAP/SMTP email config (generic, any provider)
    email_provider = models.CharField(max_length=32, blank=True, default="custom")
    email_imap_host = models.CharField(max_length=255, blank=True, default="")
    email_imap_port = models.IntegerField(default=993)
    email_smtp_host = models.CharField(max_length=255, blank=True, default="")
    email_smtp_port = models.IntegerField(default=587)
    email_imap_password = models.TextField(blank=True, default="")
    email_use_ssl = models.BooleanField(default=True)

    # Notification preferences
    email_notifications = models.BooleanField(default=True)
    push_notifications = models.BooleanField(default=True)
    webhook_url = models.URLField(blank=True, null=True)

    # Chat web tools (live search / fetch) — off until user activates
    web_tools_enabled = models.BooleanField(default=False)

    # Mock data (demo placeholder content) — off until user activates
    mock_data_enabled = models.BooleanField(default=False)

    # JOBchameleon OAuth2 email provider connexion flag (connexion only — no send)
    jc_email_connected = models.BooleanField(default=False)
    jc_email_provider = models.CharField(max_length=32, blank=True, default="")

    # Real-verified connexion flags: only True after backend successfully
    # logged into the upstream service. Decouples "credentials present" from
    # "credentials actually work", which the UI was reporting as connected
    # even when login was impossible (bad host, wrong password, stale token).
    email_verified = models.BooleanField(default=False)
    plaid_verified = models.BooleanField(default=False)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        db_table = "users"
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self):
        return self.email


class PushToken(models.Model):
    """Stores Expo push tokens for mobile and desktop clients."""

    PLATFORM_CHOICES = [
        ("ios", "iOS"),
        ("android", "Android"),
        ("web", "Web"),
        ("desktop", "Desktop"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="push_tokens",
    )
    token = models.TextField()
    platform = models.CharField(max_length=16, choices=PLATFORM_CHOICES)
    device_id = models.CharField(max_length=255, blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "token")
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.user} — {self.platform}"
