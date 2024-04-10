import json
from enum import Enum
from typing import Any

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.utils.translation import gettext_lazy as _
from django.views.generic.edit import ProcessFormView
from httpx import HTTPError
from jsonschema.validators import Draft202012Validator
from katalogus.client import get_katalogus

from octopoes.models.ooi.question import Question
from rocky.scheduler import SchedulerError


class PageActions(Enum):
    START_SCAN = "start_scan"
    SUBMIT_ANSWER = "submit_answer"
    RESCHEDULE_TASK = "reschedule_task"
    CHANGE_CLEARANCE_LEVEL = "change_clearance_level"


class PageActionsView(ProcessFormView):
    def post(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        try:
            action = request.POST.get("action", "")

            if not action:
                messages.error(request, _("Could not process your request, no action received."))

            if action == PageActions.RESCHEDULE_TASK.value:
                task_id = request.POST.get("task_id", "")
                self.reschedule_task(task_id)

            if action == PageActions.START_SCAN.value:
                boefje_id = request.POST.get("boefje_id")
                boefje = get_katalogus(self.organization.code).get_plugin(boefje_id)
                ooi_id = request.GET.get("ooi_id")
                ooi = self.get_single_ooi(pk=ooi_id)
                self.run_boefje_for_oois(boefje, [ooi])

            if action == PageActions.SUBMIT_ANSWER.value:
                if not isinstance(self.ooi, Question):
                    messages.error(request, _("Only Question OOIs can be answered."))

                schema_answer = request.POST.get("schema")
                parsed_schema_answer = json.loads(schema_answer)
                validator = Draft202012Validator(json.loads(self.ooi.json_schema))

                if not validator.is_valid(parsed_schema_answer):
                    for error in validator.iter_errors(parsed_schema_answer):
                        messages.error(request, error.message)

                self.bytes_client.upload_raw(schema_answer, {"answer", f"{self.ooi.schema_id}"}, self.ooi.ooi)
                messages.success(request, _("Question has been answered."))

            if action == PageActions.CHANGE_CLEARANCE_LEVEL.value:
                clearance_level = int(request.POST.get("level"))
                self.can_raise_clearance_level(self.ooi, clearance_level)  # returns appropriate messages

        except (SchedulerError, HTTPError) as error:
            messages.error(request, error.message)

        return self.get(request, *args, **kwargs)
