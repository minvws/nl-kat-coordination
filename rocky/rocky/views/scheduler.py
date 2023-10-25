import logging

from django.contrib import messages
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from rocky.scheduler import (
    BadRequestError,
    ConflictError,
    LazyTaskList,
    QueuePrioritizedItem,
    SchedulerError,
    Task,
    TaskNotFoundError,
    TooManyRequestsError,
    get_scheduler,
)

logger = logging.getLogger(__name__)


def schedule_task(request: HttpRequest, organization_code: str, task: QueuePrioritizedItem) -> None:
    plugin_name = ""
    input_ooi = ""
    plugin_type = task.data.type

    if plugin_type == "boefje":
        plugin_name = task.data.boefje.name
        input_ooi = task.data.input_ooi
    elif plugin_type == "normalizer":
        plugin_name = task.data.normalizer.id  # name not set yet, is None for name
        input_ooi = task.data.raw_data.boefje_meta.input_ooi
    else:
        plugin_name = _("'Plugin not found'")
        input_ooi = _("'OOI not found'")
    try:
        get_scheduler().push_task(f"{task.data.type}-{organization_code}", task)
    except (BadRequestError, TooManyRequestsError, ConflictError) as task_error:
        error_message = (
            _("Scheduling {} {} with input object {} failed. ").format(plugin_type.title(), plugin_name, input_ooi)
            + task_error.message
        )
        messages.error(request, error_message)
    except SchedulerError as error:
        messages.error(request, error.message)
    else:
        messages.success(
            request,
            _(
                "Task of {} {} with input object {} is scheduled and will soon be started in the background. "
                "Results will be added to the object list when they are in. "
                "It may take some time, a refresh of the page may be needed to show the results."
            ).format(plugin_type.title(), plugin_name, input_ooi),
        )


def get_list_of_tasks_lazy(request: HttpRequest, **params) -> LazyTaskList:
    try:
        return get_scheduler().get_lazy_task_list(**params)
    except SchedulerError as error:
        messages.error(request, error.message)
        return []


def get_details_of_task(request: HttpRequest, task_id: str) -> Task:
    try:
        return get_scheduler().get_task_details(task_id)
    except (TaskNotFoundError, TooManyRequestsError, SchedulerError) as error:
        messages.error(request, error.message)
