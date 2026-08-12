"""Circulation App — AppConfig (connects signals on startup)."""

from django.apps import AppConfig


class CirculationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.circulation"
    verbose_name = "Circulation"

    def ready(self):
        # Import signals so they are registered with Django's signal dispatcher
        import apps.circulation.signals  # noqa: F401
