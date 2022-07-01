from django.apps import AppConfig


class FMEAConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "fmea"

    def ready(self):
        import fmea.signals
