import logging
from datetime import datetime

from account.mixins import OrganizationView
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

from rocky.scheduler import PrioritizedItem, SchedulerError, SchedulerTaskList, Task, get_scheduler

logger = logging.getLogger(__name__)


def get_date_time(date: str | None) -> datetime | None:
    if date:
        return datetime.strptime(date, "%Y-%m-%d")
    return None


class SchedulerView(OrganizationView):
    task_type: str = "boefje"  # default task type

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.scheduler_client = get_scheduler(self.organization.code)
        self.scheduler_id = f"{self.task_type}-{self.organization.code}"
        self.task_type = self.request.GET.get("type", self.task_type)
        self.status = self.request.GET.get("scan_history_status", None)
        self.min_created_at = get_date_time(self.request.GET.get("scan_history_from", None))
        self.max_created_at = get_date_time(self.request.GET.get("scan_history_to", None))
        self.input_ooi = self.request.GET.get("scan_history_search", None)

    def get_task_filters(self) -> dict[str, str | datetime | None]:
        return {
            "scheduler_id": self.scheduler_id,
            "task_type": self.task_type,
            "status": self.status,
            "min_created_at": self.min_created_at,
            "max_created_at": self.max_created_at,
            "input_ooi": self.input_ooi,
        }

    def get_task_list(self) -> SchedulerTaskList | None:
        try:
            return SchedulerTaskList(self.scheduler_client, **self.get_task_filters())
        except SchedulerError as error:
            messages.error(self.request, error.message)
        return None

    def get_task_details(self, task_id: str) -> Task | None:
        try:
            return self.scheduler_client.get_task_details(task_id)
        except SchedulerError as error:
            messages.error(self.request, error.message)
        return None

    def schedule_task(self, p_item: PrioritizedItem) -> None:
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

            self.scheduler_client.push_task(p_item)

        except SchedulerError as error:
            messages.error(self.request, error.message)
        else:
            messages.success(
                self.request,
                _(
                    "Your task is scheduled and will soon be started in the background. "
                    "Results will be added to the object list when they are in. "
                    "It may take some time, a refresh of the page may be needed to show the results."
                ),
            )

    # FIXME: Tasks should be (re)created with supplied data, not by fetching prior
    # task info from the scheduler. Task data should be available from the context
    # from which the task is created.
    def reschedule_task(self, task_id: str) -> None:
        try:
            task = self.scheduler_client.get_task_details(task_id)
            new_p_item = PrioritizedItem(
                data=task.p_item.data,
                priority=1,
            )

            self.schedule_task(new_p_item)
        except SchedulerError as error:
            messages.error(self.request, error.message)
