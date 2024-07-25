from django.apps import AppConfig


class RockyConfig(AppConfig):
    name = "rocky"

    def ready(self):
        from . import signals  # noqa: F401
