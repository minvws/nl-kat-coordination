import json
from collections import defaultdict
from datetime import datetime, timezone
from enum import Enum

from django.contrib import messages
from django.core.paginator import Page, Paginator
from django.http import Http404
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _
from httpx import HTTPError
from jsonschema.validators import Draft202012Validator
from katalogus.client import get_katalogus
from katalogus.utils import get_enabled_boefjes_for_ooi_class
from tools.forms.base import ObservedAtForm
from tools.forms.ooi import PossibleBoefjesFilterForm
from tools.models import Indemnification
from tools.ooi_helpers import format_display

from octopoes.models import OOI, Reference
from octopoes.models.ooi.question import Question
from rocky.views.ooi_detail_related_object import OOIFindingManager, OOIRelatedObjectAddView
from rocky.views.ooi_view import BaseOOIDetailView
from rocky.views.scheduler import SchedulerView


class PageActions(Enum):
    START_SCAN = "start_scan"
    SUBMIT_ANSWER = "submit_answer"
    RESCHEDULE_TASK = "reschedule_task"
    CHANGE_CLEARANCE_LEVEL = "change_clearance_level"


class OOIDetailView(
    SchedulerView,
    OOIRelatedObjectAddView,
    OOIFindingManager,
    BaseOOIDetailView,
):
    template_name = "oois/ooi_detail.html"
    connector_form_class = ObservedAtForm
    task_history_limit = 10

    def post(self, request, *args, **kwargs):
        if not self.indemnification_present:
            messages.add_message(
                request, messages.ERROR, f"Indemnification not present at organization {self.organization}."
            )
            return self.get(request, status_code=403, *args, **kwargs)

        if "action" not in self.request.POST:
            return self.get(request, status_code=404, *args, **kwargs)

        self.ooi = self.get_ooi()

        action = self.request.POST.get("action")
        return self.handle_page_action(action)

    def handle_page_action(self, action: str) -> bool:
        try:
            if action == PageActions.CHANGE_CLEARANCE_LEVEL.value:
                clearance_level = int(self.request.POST.get("level"))
                if not self.can_raise_clearance_level(self.ooi, clearance_level):
                    return redirect("account_detail", organization_code=self.organization.code)
                return self.get(self.request, *self.args, **self.kwargs)

            if action == PageActions.RESCHEDULE_TASK.value:
                task_id = self.request.POST.get("task_id", "")
                self.reschedule_task(task_id)

            if action == PageActions.START_SCAN.value:
                boefje_id = self.request.POST.get("boefje_id")
                ooi_id = self.request.GET.get("ooi_id")

                boefje = get_katalogus(self.organization.code).get_plugin(boefje_id)
                ooi = self.get_single_ooi(pk=ooi_id)
                self.run_boefje_for_oois(boefje, [ooi])
                return redirect("task_list", organization_code=self.organization.code)

            if action == PageActions.SUBMIT_ANSWER.value:
                if not isinstance(self.ooi, Question):
                    messages.add_message(self.request, messages.ERROR, _("Only Question OOIs can be answered."))
                    return self.get(self.request, status_code=500, *self.args, **self.kwargs)

                schema_answer = self.request.POST.get("schema")
                parsed_schema_answer = json.loads(schema_answer)
                validator = Draft202012Validator(json.loads(self.ooi.json_schema))

                if not validator.is_valid(parsed_schema_answer):
                    for error in validator.iter_errors(parsed_schema_answer):
                        messages.add_message(self.request, messages.ERROR, error.message)

                    return self.get(self.request, status_code=422, *self.args, **self.kwargs)

                self.bytes_client.upload_raw(schema_answer, {"answer", f"{self.ooi.schema_id}"}, self.ooi.ooi)
                messages.add_message(self.request, messages.SUCCESS, "Question has been answered.")
                return self.get(self.request, status_code=201, *self.args, **self.kwargs)

            return self.get(self.request, status_code=404, *self.args, **self.kwargs)
        except HTTPError as exception:
            messages.add_message(self.request, messages.ERROR, f"{action} failed: '{exception}'")
            return self.get(self.request, status_code=500, *self.args, **self.kwargs)

    def get_current_ooi(self) -> OOI | None:
        # self.ooi is already the current state of the OOI
        if self.observed_at.date() == datetime.utcnow().date():
            return self.ooi
        try:
            return self.get_ooi(pk=self.get_ooi_id(), observed_at=datetime.now(timezone.utc))
        except Http404:
            return None

    def get_organization_indemnification(self):
        return Indemnification.objects.filter(organization=self.organization).exists()

    def get_task_filters(self) -> dict[str, str | datetime | None]:
        filters = super().get_task_filters()
        filters["task_type"] = "boefje"
        filters["input_ooi"] = self.get_ooi_id()
        return filters

    def get_task_history(self) -> Page:
        page = int(self.request.GET.get("task_history_page", 1))

        task_list = self.get_task_list()

        return Paginator(task_list, self.task_history_limit).page(page)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        filter_form = PossibleBoefjesFilterForm(self.request.GET)

        # List from katalogus
        boefjes = []
        if self.get_organization_indemnification():
            boefjes = get_enabled_boefjes_for_ooi_class(self.ooi.__class__, self.organization)

        if boefjes:
            context["enabled_boefjes_available"] = True

        max_level = self.organization_member.acknowledged_clearance_level
        if self.ooi.scan_profile and filter_form.is_valid() and not filter_form.cleaned_data["show_all"]:
            max_level = min(max_level, self.ooi.scan_profile.level)

        context["boefjes"] = [boefje for boefje in boefjes if boefje.scan_level.value <= max_level]
        context["ooi"] = self.ooi

        declarations, observations, inferences = self.get_origins(self.ooi.reference, self.organization)

        inference_params = self.octopoes_api_connector.list_origin_parameters(
            {inference.origin.id for inference in inferences},
            self.observed_at,
        )
        inference_params_per_inference = defaultdict(list)
        for inference_param in inference_params:
            inference_params_per_inference[inference_param.origin_id].append(inference_param)

        inference_origin_params: list[tuple] = []
        for inference in inferences:
            inference_origin_params.append((inference, inference_params_per_inference[inference.origin.id]))

        context["declarations"] = declarations
        context["observations"] = observations
        context["inferences"] = inferences
        context["inference_origin_params"] = inference_origin_params
        context["member"] = self.organization_member

        # TODO: generic solution to render ooi fields properly: https://github.com/minvws/nl-kat-coordination/issues/145
        context["object_details"] = format_display(self.get_ooi_properties(self.ooi), ignore=["json_schema"])
        context["ooi_types"] = self.get_ooi_types_input_values(self.ooi)
        context["observed_at_form"] = self.get_connector_form()
        context["observed_at"] = self.observed_at
        context["is_question"] = isinstance(self.ooi, Question)
        context["ooi_past_due"] = context["observed_at"].date() < datetime.utcnow().date()
        context["related"] = self.get_related_objects(context["observed_at"])
        context["ooi_current"] = self.get_current_ooi()

        context["count_findings_per_severity"] = dict(self.count_findings_per_severity())
        context["severity_summary_totals"] = sum(context["count_findings_per_severity"].values())

        context["possible_boefjes_filter_form"] = filter_form
        context["organization_indemnification"] = self.get_organization_indemnification()
        context["task_history"] = self.get_task_history()
        context["task_history_form_fields"] = [
            "task_history_from",
            "task_history_to",
            "task_history_status",
            "task_history_search",
            "task_history_page",
        ]
        if self.request.GET.get("show_clearance_level_inheritance"):
            clearance_level_inheritance = self.get_scan_profile_inheritance(self.ooi)
            formatted_inheritance = [
                {
                    "object_type": Reference.from_str(section.reference).class_,
                    "primary_key": section.reference,
                    "human_readable": Reference.from_str(section.reference).human_readable,
                    "level": section.level,
                }
                for section in clearance_level_inheritance
            ]
            context["clearance_level_inheritance"] = formatted_inheritance
        return context
