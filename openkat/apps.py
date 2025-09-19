from django.apps import AppConfig


class OpenKATConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "openkat"

    def ready(self):
        # import the signals module to ensure that the signal handlers are connected
        # and to avoid "apps aren't loaded yet" error from Django
        from . import signals  # noqa: F401, PLC0415
