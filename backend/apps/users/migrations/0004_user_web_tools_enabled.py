from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0003_user_jira_api_token_user_jira_email_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="web_tools_enabled",
            field=models.BooleanField(default=False),
        ),
    ]
