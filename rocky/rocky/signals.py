from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from structlog import get_logger

logger = get_logger(__name__)


# Signal sent when a user logs in
@receiver(user_logged_in)
def user_logged_in_callback(sender, request, user, **kwargs):
    logger.info("User logged in", username=user.get_username())

import structlog
from django.contrib.admin.models import LogEntry

logger = structlog.get_logger(__name__)

# Signal sent when a user logs out
@receiver(user_logged_out)
def user_logged_out_callback(sender, request, user, **kwargs):
    logger.info("User logged out", userername=user.get_username())


# Signal sent when a user login attempt fails
@receiver(user_login_failed)
def user_login_failed_callback(sender, credentials, request, **kwargs):
    logger.info("User login failed", credentials=credentials)

def log_save(sender, instance, created, **kwargs) -> None:
    if isinstance(instance, LogEntry):
        # Django admin will automatically create a LogEntry for each admin
        # action, but we shouldn't send log messages about these.
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
