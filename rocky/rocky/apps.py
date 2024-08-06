from django.apps import AppConfig
from django.db.models.signals import post_delete, post_save


class RockyConfig(AppConfig):
    name = "rocky"

    def ready(self) -> None:
        # We need to do the import here because else we will get an "apps aren't
        # loaded yet" error from Django.
        from rocky.signals import log_delete, log_save

        post_save.connect(log_save, dispatch_uid="log_save")
        post_delete.connect(log_delete, dispatch_uid="log_delete")
