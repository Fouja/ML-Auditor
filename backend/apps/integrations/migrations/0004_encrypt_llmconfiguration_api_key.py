from django.db import migrations, models

from config.security import encrypt_secret, is_encrypted


def encrypt_plaintext_keys(apps, schema_editor):
    LLMConfiguration = apps.get_model("integrations", "LLMConfiguration")
    for row in LLMConfiguration.objects.all().exclude(api_key="").iterator():
        if row.api_key and not is_encrypted(row.api_key):
            row.api_key = encrypt_secret(row.api_key)
            row.save(update_fields=["api_key"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("integrations", "0003_alter_integrationconnection_service"),
    ]

    operations = [
        migrations.AlterField(
            model_name="llmconfiguration",
            name="api_key",
            field=models.CharField(max_length=1000),
        ),
        migrations.RunPython(encrypt_plaintext_keys, noop),
    ]
