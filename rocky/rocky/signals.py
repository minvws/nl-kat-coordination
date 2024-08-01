import structlog
from django.contrib.admin.models import LogEntry

logger = structlog.get_logger(__name__)


def log_save(sender, instance, created, **kwargs) -> None:
    if isinstance(instance, LogEntry):
        # Django admin will automatically create a LogEntry for each admin
        # action, but we shouldn't send log messages about thosee.
        return

    if created:
        logger.info(
            "%s %s created",
            instance._meta.object_name,
            instance,
            object_type=instance._meta.object_name,
            object=str(instance),
        )
    else:
        logger.info(
            "%s %s updated",
            instance._meta.object_name,
            instance,
            object_type=instance._meta.object_name,
            object=str(instance),
        )


def log_delete(sender, instance, **kwargs) -> None:
    logger.info(
        "%s %s deleted",
        instance._meta.object_name,
        instance,
        object_type=instance._meta.object_name,
        object=str(instance),
    )
