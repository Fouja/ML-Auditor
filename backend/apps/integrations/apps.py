from django.apps import AppConfig


class IntegrationsConfig(AppConfig):
    default_auto_field = "django.db.BigAutoField"
    name = "apps.integrations"
    verbose_name = "Integrations"

    def ready(self):
        # Import signal receivers so integration events are mirrored to the
        # structured log pipeline.
        import apps.integrations.signals  # noqa: F401
