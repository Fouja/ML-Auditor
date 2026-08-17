from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Conversation",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("agent_type", models.CharField(default="general", max_length=50)),
                ("title", models.CharField(blank=True, default="", max_length=500)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="agent_conversations",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "agent_conversations",
                "ordering": ["-updated_at"],
            },
        ),
        migrations.CreateModel(
            name="ConversationMessage",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "role",
                    models.CharField(
                        choices=[
                            ("user", "User"),
                            ("assistant", "Assistant"),
                            ("system", "System"),
                        ],
                        max_length=20,
                    ),
                ),
                ("content", models.TextField()),
                ("metadata", models.JSONField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "conversation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="messages",
                        to="agents.conversation",
                    ),
                ),
            ],
            options={
                "db_table": "agent_conversation_messages",
                "ordering": ["created_at"],
                "indexes": [
                    models.Index(
                        fields=["conversation", "created_at"],
                        name="agent_conve_convers_5c5012_idx",
                    )
                ],
            },
        ),
        migrations.AddIndex(
            model_name="conversation",
            index=models.Index(
                fields=["user", "agent_type", "-updated_at"],
                name="agent_conve_user_id_b0c73b_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="conversation",
            constraint=models.UniqueConstraint(
                fields=("user", "agent_type"), name="uniq_user_agent_conversation"
            ),
        ),
    ]
