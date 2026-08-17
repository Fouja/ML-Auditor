from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("workspace", "0004_newsarticle_image_url"),
    ]

    operations = [
        migrations.CreateModel(
            name="GeneratedDocument",
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
                ("title", models.CharField(max_length=500)),
                ("content", models.TextField(blank=True, default="")),
                (
                    "doc_format",
                    models.CharField(
                        choices=[
                            ("presentation", "Presentation"),
                            ("article", "Article"),
                        ],
                        default="presentation",
                        max_length=30,
                    ),
                ),
                (
                    "file_format",
                    models.CharField(
                        choices=[
                            ("docx", "Word (DOCX)"),
                            ("pptx", "PowerPoint (PPTX)"),
                            ("md", "Markdown"),
                        ],
                        default="pptx",
                        max_length=10,
                    ),
                ),
                ("style", models.CharField(default="professional", max_length=30)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "note",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="generated_documents",
                        to="workspace.note",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="workspace_generated_documents",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-updated_at"],
                "indexes": [
                    models.Index(
                        fields=["user", "doc_format"],
                        name="workspace_g_user_id_76aea4_idx",
                    )
                ],
            },
        ),
    ]
