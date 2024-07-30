from django.apps import AppConfig


class RockyConfig(AppConfig):
    name = "rocky"

    def ready(self):
        # import the signals module to ensure that the signal handlers are connected
        from . import signals  # noqa: F401
