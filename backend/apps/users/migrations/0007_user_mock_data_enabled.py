from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0006_user_email_verified_user_plaid_verified"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="mock_data_enabled",
            field=models.BooleanField(default=False),
        ),
    ]
