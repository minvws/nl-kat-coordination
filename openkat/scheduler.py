from __future__ import annotations

import collections
from typing import Any

import structlog
from django.utils.translation import gettext_lazy as _

from openkat.celery import app
from openkat.models import Organization
from tasks.models import Schedule, Task

logger = structlog.get_logger(__name__)


class SchedulerError(Exception):
    message: str = _("The Scheduler has an unexpected error. Check the Scheduler logs for further details.")

    def __init__(self, *args: object, extra_message: str | None = None) -> None:
        super().__init__(*args)
        if extra_message is not None:
            self.message = extra_message + self.message

    def __str__(self) -> str:
        return str(self.message)


class SchedulerTaskNotFound(SchedulerError):
    message = _("Task could not be found.")


class SchedulerClient:
    def __init__(self, organization: Organization | None):  # TODO
        self.organization_code = organization.code if organization else None

    def push_task(self, task: Task) -> None:
        if task.type == "boefje":
            if task.data["boefje"]["oci_image"]:
                app.send_task(
                    "openkat.tasks.docker_boefje",
                    (task.organization.code, task.data["boefje"]["plugin_id"], task.data["input_ooi"]),
                    task_id=str(task.id),
                )
            else:
                app.send_task(
                    "openkat.tasks.boefje",
                    (task.organization.code, task.data["boefje"]["plugin_id"], task.data["input_ooi"]),
                    task_id=str(task.id),
                )
        if task.type == "normalizer":
            app.send_task(
                "openkat.tasks.normalizer",
                (task.organization.code, task.data["normalizer"]["plugin_id"], task.data["raw_data"]["id"]),
                task_id=str(task.id),
            )
        if task.type == "report":
            app.send_task(
                "openkat.tasks.report", (task.organization.code, task.data["report_recipe_id"]), task_id=str(task.id)
            )

    def get_task_stats(self, scheduler_id: str, organisation_id: str | None = None) -> dict[str, int]:
        return {"queued": 0, "running": 0, "failed": 0, "completed": 0, "total": 0}  # TODO

    @staticmethod
    def _merge_stat_dicts(dicts: list[dict]) -> dict:
        """Merge multiple stats dicts."""
        stat_sum: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
        for dct in dicts:
            for timeslot, counts in dct.items():
                stat_sum[timeslot].update(counts)
        return dict(stat_sum)

    def get_task_stats_for_all_organizations(self, scheduler_id: str) -> dict:
        return self.get_task_stats(scheduler_id)

    def get_combined_schedulers_stats(self, scheduler_id: str, organization_codes: list[str]) -> dict:
        """Return merged stats for a set of scheduler ids."""
        return self._merge_stat_dicts(
            dicts=[self.get_task_stats(scheduler_id, org_code) for org_code in organization_codes]
        )

    def get_scheduled_reports(self) -> list[dict[str, Any]]:
        schedules = Schedule.objects.filter(organization__code=self.organization_code, type="report")

        return list(schedules.values())


def scheduler_client(organization: Organization | None) -> SchedulerClient:
    return SchedulerClient(organization)
