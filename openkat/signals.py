import datetime

from django.conf import settings
from django.contrib.admin.models import LogEntry
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from structlog import get_logger

from crisis_room.management.commands.dashboards import get_or_create_default_dashboard
from files.models import File
from octopoes.api.models import Declaration
from octopoes.models.ooi.network import Network
from octopoes.xtdb.exceptions import XTDBException
from openkat.exceptions import OctopoesException
from openkat.models import Organization
from tasks.new_tasks import process_raw_file

logger = get_logger(__name__)


# Signal sent when a user logs in
@receiver(user_logged_in)
def user_logged_in_callback(sender, request, user, **kwargs):
    logger.info("User logged in", username=user.get_username())


# Signal sent when a user logs out
@receiver(user_logged_out)
def user_logged_out_callback(sender, request, user, **kwargs):
    logger.info("User logged out", userername=user.get_username())


# Signal sent when a user login attempt fails
@receiver(user_login_failed)
def user_login_failed_callback(sender, credentials, request, **kwargs):
    logger.info("User login failed", credentials=credentials)


# Signal sent when a model is saved
@receiver(post_save, dispatch_uid="log_save")
def log_save(sender, instance, created, **kwargs) -> None:
    if isinstance(instance, LogEntry):
        # Django admin will automatically create a LogEntry for each admin
        # action, but we shouldn't send log messages about these.
        return

    context = {}
    event_codes = getattr(instance, "EVENT_CODES", None)

    if created:
        if event_codes and "created" in event_codes:
            context["event_code"] = event_codes["created"]
        logger.info(
            "%s %s created",
            instance._meta.object_name,
            instance,
            object_type=instance._meta.object_name,
            object=str(instance),
            **context,
        )
    else:
        if event_codes and "updated" in event_codes:
            context["event_code"] = event_codes["updated"]
        logger.info(
            "%s %s updated",
            instance._meta.object_name,
            instance,
            object_type=instance._meta.object_name,
            object=str(instance),
            **context,
        )


# Signal sent when a model is deleted
@receiver(post_delete, dispatch_uid="log_delete")
def log_delete(sender, instance, **kwargs) -> None:
    context = {}
    event_codes = getattr(instance, "EVENT_CODES", None)
    if event_codes and "deleted" in event_codes:
        context["event_code"] = event_codes["deleted"]
    logger.info(
        "%s %s deleted",
        instance._meta.object_name,
        instance,
        object_type=instance._meta.object_name,
        object=str(instance),
        **context,
    )


@receiver(pre_save, sender=Organization)
def organization_pre_save(sender, instance, *args, **kwargs):
    instance.clean()
    octopoes_client = settings.OCTOPOES_FACTORY(instance.code)

    try:
        octopoes_client.create_node()
    except XTDBException as e:
        raise OctopoesException("Failed creating organization in Octopoes") from e


@receiver(post_save, sender=Organization)
def organization_post_save(sender, instance, created, *args, **kwargs):
    octopoes_client = settings.OCTOPOES_FACTORY(instance.code)

    # will trigger only when new organization is created, not for updating.
    if created:
        get_or_create_default_dashboard(instance, octopoes_client)

    try:
        valid_time = datetime.datetime.now(datetime.timezone.utc)
        octopoes_client.save_declaration(Declaration(ooi=Network(name="internet"), valid_time=valid_time))
    except Exception:
        logger.exception("Could not seed internet for organization %s", sender)


@receiver(post_save, sender=File)
def file_post_save(sender, instance, created, *args, **kwargs):
    if created:
        process_raw_file(instance)
