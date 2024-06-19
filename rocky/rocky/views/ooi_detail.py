import json
from collections import defaultdict
from datetime import datetime

from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from jsonschema.validators import Draft202012Validator
from katalogus.client import get_katalogus
from katalogus.utils import get_enabled_boefjes_for_ooi_class
from tools.forms.ooi import PossibleBoefjesFilterForm
from tools.forms.scheduler import OOIDetailTaskFilterForm
from tools.ooi_helpers import format_display

from octopoes.models import Reference
from octopoes.models.ooi.question import Question
from rocky.views.ooi_detail_related_object import OOIFindingManager, OOIRelatedObjectAddView
from rocky.views.ooi_view import BaseOOIDetailView
from rocky.views.tasks import TaskListView


class OOIDetailView(
    BaseOOIDetailView,
    OOIRelatedObjectAddView,
    OOIFindingManager,
    TaskListView,
):
    template_name = "oois/ooi_detail.html"
    task_filter_form = OOIDetailTaskFilterForm
    task_type = "boefje"

    def post(self, request, *args, **kwargs):
        if self.action == self.CHANGE_CLEARANCE_LEVEL:
            self.set_clearance_level()
        if self.action == self.SUBMIT_ANSWER:
            self.answer_ooi_questions()
        if self.action == self.START_SCAN:
            self.start_boefje_scan()
        return super().post(request, *args, **kwargs)

    def set_clearance_level(self) -> None:
        if not self.indemnification_present:
            return self.indemnification_error()
        else:
            clearance_level = int(self.request.POST.get("level"))
            self.can_raise_clearance_level(self.ooi, clearance_level)  # returns appropriate messages

    def answer_ooi_questions(self) -> None:
        if not isinstance(self.ooi, Question):
            messages.error(self.request, _("Only Question OOIs can be answered."))
            return

        schema_answer = self.request.POST.get("schema", "")
        parsed_schema_answer = json.loads(schema_answer)
        validator = Draft202012Validator(json.loads(self.ooi.json_schema))

        if not validator.is_valid(parsed_schema_answer):
            for error in validator.iter_errors(parsed_schema_answer):
                messages.error(self.request, error.message)
            return

        self.bytes_client.upload_raw(schema_answer, {"answer", f"{self.ooi.schema_id}"}, self.ooi.ooi)
        messages.success(self.request, _("Question has been answered."))

    def start_boefje_scan(self) -> None:
        boefje_id = self.request.POST.get("boefje_id")
        boefje = get_katalogus(self.organization.code).get_plugin(boefje_id)
        ooi_id = self.request.GET.get("ooi_id")
        ooi = self.get_single_ooi(pk=ooi_id)
        self.run_boefje(boefje, ooi)

    def get_task_filters(self) -> dict[str, str | datetime | None]:
        filters = super().get_task_filters()
        filters["input_ooi"] = self.ooi.primary_key  # shows only tasks for this particular ooi
        return filters

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        filter_form = PossibleBoefjesFilterForm(self.request.GET)

        # List from katalogus
        boefjes = []
        if self.indemnification_present:
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

        context["is_question"] = isinstance(self.ooi, Question)
        context["ooi_past_due"] = context["observed_at"].date() < datetime.utcnow().date()
        context["related"] = self.get_related_objects(context["observed_at"])

        context["count_findings_per_severity"] = dict(self.count_findings_per_severity())
        context["severity_summary_totals"] = sum(context["count_findings_per_severity"].values())

        context["possible_boefjes_filter_form"] = filter_form
        context["organization_indemnification"] = self.indemnification_present

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
