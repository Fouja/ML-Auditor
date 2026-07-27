import uuid

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
