from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0004_user_web_tools_enabled"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="jc_email_connected",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="user",
            name="jc_email_provider",
            field=models.CharField(blank=True, default="", max_length=32),
        ),
    ]
