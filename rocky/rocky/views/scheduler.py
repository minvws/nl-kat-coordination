from datetime import datetime
from typing import Any

from django.contrib import messages
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _
from katalogus.client import Boefje, Normalizer
from tools.forms.scheduler import TaskFilterForm

from octopoes.models import OOI
from rocky.scheduler import Boefje as SchedulerBoefje
from rocky.scheduler import (
    BoefjeTask,
    LazyTaskList,
    NormalizerTask,
    PrioritizedItem,
    RawData,
    SchedulerError,
    SchedulerValidationError,
    Task,
    scheduler_client,
)
from rocky.scheduler import Normalizer as SchedulerNormalizer
from rocky.views.mixins import OctopoesView


def get_date_time(date: str | None) -> datetime | None:
    if date:
        return datetime.strptime(date, "%Y-%m-%d")
    return None


class SchedulerView(OctopoesView):
    task_type: str = "boefje"  # default task type
    task_filter_form = TaskFilterForm

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.scheduler_client = scheduler_client(self.organization.code)

    def get_task_filters(self) -> dict[str, Any]:
        return {
            "scheduler_id": f"{self.task_type}-{self.organization.code}",
            "task_type": self.request.GET.get("type", self.task_type),
            "plugin_id": None,  # plugin_id present and set at plugin detail
            **self.get_form_data(),
        }

    def get_form_data(self) -> dict[str, Any]:
        form_data = self.get_task_filter_form().data.dict()
        return {k: v for k, v in form_data.items() if v}

    def get_task_filter_form(self) -> TaskFilterForm:
        return self.task_filter_form(self.request.GET)

    def get_task_list(self) -> LazyTaskList | list[Any]:
        try:
            return LazyTaskList(self.scheduler_client, **self.get_task_filters())
        except (SchedulerValidationError, SchedulerError) as error:
            messages.error(self.request, error.message)
        return []

    def get_task_details(self, task_id: str) -> Task | None:
        try:
            return self.scheduler_client.get_task_details(task_id)
        except SchedulerError as error:
            return messages.error(self.request, error.message)

    def get_output_oois(self, task):
        try:
            return self.octopoes_api_connector.list_origins(
                valid_time=task.p_item.data.raw_data.boefje_meta.ended_at,
                task_id=task.id,
            )[0].result
        except IndexError:
            return []
        except SchedulerError as error:
            messages.error(self.request, error.message)
            return []

    def get_json_task_details(self) -> JsonResponse | None:
        try:
            task = self.get_task_details(self.kwargs["task_id"])
            if task:
                return JsonResponse(
                    {
                        "oois": self.get_output_oois(task),
                        "valid_time": task.p_item.data.raw_data.boefje_meta.ended_at.strftime("%Y-%m-%dT%H:%M:%S"),
                    },
                    safe=False,
                )
            return task
        except SchedulerError as error:
            return messages.error(self.request, error.message)

    def schedule_task(self, p_item: PrioritizedItem) -> None:
        if not self.indemnification_present:
            return self.indemnification_error()
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
        if not self.indemnification_present:
            return self.indemnification_error()
        try:
            task = self.scheduler_client.get_task_details(task_id)

            new_p_item = PrioritizedItem(
                data=task.p_item.data,
                priority=1,
            )

            self.schedule_task(new_p_item)
        except SchedulerError as error:
            messages.error(self.request, error.message)

    def run_normalizer(self, katalogus_normalizer: Normalizer, raw_data: RawData) -> None:
        if not self.indemnification_present:
            return self.indemnification_error()
        try:
            normalizer_task = NormalizerTask(
                normalizer=SchedulerNormalizer.model_validate(katalogus_normalizer.model_dump()),
                raw_data=raw_data,
            )

            p_item = PrioritizedItem(priority=1, data=normalizer_task)

            self.schedule_task(p_item)
        except SchedulerError as error:
            messages.error(self.request, error.message)

    def run_boefje(self, katalogus_boefje: Boefje, ooi: OOI | None) -> None:
        if not self.indemnification_present:
            return self.indemnification_error()
        try:
            boefje_task = BoefjeTask(
                boefje=SchedulerBoefje.model_validate(katalogus_boefje.model_dump()),
                input_ooi=ooi.reference if ooi else None,
                organization=self.organization.code,
            )

            p_item = PrioritizedItem(priority=1, data=boefje_task)
            if ooi and ooi is not None and ooi.scan_profile and ooi.scan_profile.level < katalogus_boefje.scan_level:
                self.schedule_task(p_item)
        except SchedulerError as error:
            messages.error(self.request, error.message)

    def run_boefje_for_oois(
        self,
        boefje: Boefje,
        oois: list[OOI],
    ) -> None:
        try:
            if not oois and not boefje.consumes:
                self.run_boefje(boefje, None)

            for ooi in oois:
                self.run_boefje(boefje, ooi)

        except SchedulerError as error:
            messages.error(self.request, error.message)
