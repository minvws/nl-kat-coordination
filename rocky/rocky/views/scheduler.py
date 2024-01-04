import logging
from typing import List, Optional

from django.contrib import messages
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from rocky.scheduler import (
    PrioritizedItem,
    SchedulerError,
    SchedulerTaskList,
    Task,
    TaskNotFoundError,
    TooManyRequestsError,
    get_scheduler,
)

logger = logging.getLogger(__name__)


def get_list_of_tasks(request: HttpRequest, organization_code: str, **params) -> List[Task]:
    try:
        client = get_scheduler(organization_code)
        return SchedulerTaskList(client, **params)
    except SchedulerError as error:
        messages.error(request, error.message)
    return []


def get_details_of_task(request: HttpRequest, organization_code: str, task_id: str) -> Optional[Task]:
    try:
        return get_scheduler(organization_code).get_task_details(task_id)
    except (TaskNotFoundError, TooManyRequestsError, SchedulerError) as error:
        messages.error(request, error.message)


def schedule_task(request: HttpRequest, organization_code: str, p_item: PrioritizedItem) -> None:
    try:
        # Remove id attribute of both p_item and p_item.data, since the
        # scheduler will create a new task with new id's. However, pydantic
        # requires an id attribute to be present in its definition and the
        # default set to None when the attribute is optional, otherwise it
        # will not serialize the id if it is not present in the definition.
        if hasattr(p_item, "id"):
            delattr(p_item, "id")

        if hasattr(p_item.data, "id"):
            delattr(p_item.data, "id")

        scheduler_client = get_scheduler(organization_code)
        scheduler_client.push_task(p_item)

    except SchedulerError as error:
        messages.error(request, error.message)
    else:
        messages.success(
            request,
            _(
                "Your task is scheduled and will soon be started in the background. "
                "Results will be added to the object list when they are in. "
                "It may take some time, a refresh of the page may be needed to show the results."
            ),
        )


# FIXME: Tasks should be (re)created with supplied data, not by fetching prior
# task info from the scheduler. Task data should be available from the context
# from which the task is created.
def reschedule_task(request: HttpRequest, organization_code: str, task_id: str) -> None:
    try:
        scheduler_client = get_scheduler(organization_code)
        task = scheduler_client.get_task_details(task_id)
    except SchedulerError as error:
        messages.error(request, error.message)
        return

    if not task:
        messages.error(request, _("Task not found."))
        return

    try:
        new_p_item = PrioritizedItem(
            data=task.p_item.data,
            priority=1,
        )

        schedule_task(request, organization_code, new_p_item)
    except SchedulerError as error:
        messages.error(request, error.message)
        return
