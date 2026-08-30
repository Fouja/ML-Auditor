# Generated data migration: copy existing single-account tokens from User
# into IntegrationConnection so the new multi-account model keeps working.

from django.conf import settings
from django.db import migrations


def copy_user_tokens_to_connections(apps, schema_editor):
    User = apps.get_model(settings.AUTH_USER_MODEL)
    IntegrationConnection = apps.get_model("integrations", "IntegrationConnection")

    for user in User.objects.all():
        # Gmail / Google OAuth
        if user.google_access_token:
            label = user.email or "Gmail"
            conn, created = IntegrationConnection.objects.get_or_create(
                user=user,
                service="gmail",
                account_label=label,
                defaults={
                    "access_token": user.google_access_token,
                    "refresh_token": user.google_refresh_token or "",
                    "status": "active",
                    "is_active": True,
                },
            )
            if not created:
                conn.access_token = user.google_access_token
                conn.refresh_token = user.google_refresh_token or ""
                conn.is_active = True
                conn.save(update_fields=["access_token", "refresh_token", "is_active"])

        # Plaid
        if user.plaid_access_token:
            conn, created = IntegrationConnection.objects.get_or_create(
                user=user,
                service="plaid",
                account_label="Plaid",
                defaults={
                    "access_token": user.plaid_access_token,
                    "status": "active",
                    "is_active": True,
                },
            )
            if not created:
                conn.access_token = user.plaid_access_token
                conn.is_active = True
                conn.save(update_fields=["access_token", "is_active"])


def reverse_migration(apps, schema_editor):
    # No-op reverse: we do not delete user tokens on rollback to avoid data loss.
    pass


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("integrations", "0006_alter_integrationconnection_unique_together_and_more"),
    ]

    operations = [
        migrations.RunPython(copy_user_tokens_to_connections, reverse_migration),
    ]
