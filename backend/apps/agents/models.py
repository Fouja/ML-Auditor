"""
Chat conversation models for the Argus agent.
Persistent, per-user conversation history backed by Postgres instead of
the old in-memory store, so context survives restarts.
"""

import uuid

from django.conf import settings
from django.db import models


class Conversation(models.Model):
    """A conversation thread between a user and an agent."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="agent_conversations",
    )
    agent_type = models.CharField(max_length=50, default="general")
    title = models.CharField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "agent_conversations"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["user", "agent_type", "-updated_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "agent_type"],
                name="uniq_user_agent_conversation",
            )
        ]

    def __str__(self):
        return f"{self.user.email} / {self.agent_type}"


class ConversationMessage(models.Model):
    """A single turn (user or assistant) inside a conversation."""

    ROLE_CHOICES = [
        ("user", "User"),
        ("assistant", "Assistant"),
        ("system", "System"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    metadata = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "agent_conversation_messages"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["conversation", "created_at"]),
        ]

    def __str__(self):
        return f"{self.role}: {self.content[:60]}"
