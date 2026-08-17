# Generated manually to add the IMAP email source type for email clustering.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("data_streams", "0003_alter_datastream_source_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="datastream",
            name="source_type",
            field=models.CharField(
                choices=[
                    ("gmail", "Gmail"),
                    ("kijiji", "Kijiji"),
                    ("plaid", "Plaid"),
                    ("google_calendar", "Google Calendar"),
                    ("manual", "Manual Entry"),
                    ("jira", "Jira"),
                    ("email", "Email (IMAP)"),
                ],
                max_length=50,
            ),
        ),
    ]
