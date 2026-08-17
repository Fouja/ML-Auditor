# Generated manually for the ML-Auditor email-clustering categories.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("document_chunks", "0002_alter_documentchunk_cluster_category"),
    ]

    operations = [
        migrations.AlterField(
            model_name="documentchunk",
            name="cluster_category",
            field=models.CharField(
                choices=[
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
                ],
                default="general",
                max_length=100,
            ),
        ),
    ]
