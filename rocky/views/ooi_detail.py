from datetime import datetime, timezone
from enum import Enum
from typing import List
from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _

from octopoes.models import OOI
from requests.exceptions import RequestException

from rocky.katalogus import get_enabled_boefjes_for_ooi_class, get_katalogus
from rocky.views.boefje import BoefjeMixin
from rocky.views.ooi_detail_related_object import OOIRelatedObjectAddView
from rocky.views.ooi_view import BaseOOIDetailView, OOIBreadcrumbsMixin
from tools.forms import ObservedAtForm
from tools.ooi_helpers import format_display
from tools.view_helpers import Breadcrumb


class PageActions(Enum):
    START_SCAN = "start_scan"


class OOIDetailView(
    OOIRelatedObjectAddView,
    BaseOOIDetailView,
    BoefjeMixin,
    OOIBreadcrumbsMixin,
):
    template_name = "oois/ooi_detail.html"
    connector_form_class = ObservedAtForm

    def post(self, request, *args, **kwargs):
        if "action" not in self.request.POST:
            return self.get(request, *args, **kwargs)
        self.ooi = self.get_ooi()
        action_success = self.handle_page_action(request.POST.get("action"))
        if not action_success:
            return self.get(request, *args, **kwargs)

        success_message = "Your scan is running successfully in the background. \n Results will be added to the object list when they are in. It may take some time, a refresh of the page may be needed to show the results."
        messages.add_message(request, messages.SUCCESS, success_message)

        return redirect("task_list")

    def handle_page_action(self, action: str) -> bool:
        try:
            if action == PageActions.START_SCAN.value:
                boefje_id = self.request.POST.get("boefje_id")
                ooi_id = self.request.GET.get("ooi_id")

                boefje = get_katalogus(
                    self.request.active_organization.code
                ).get_boefje(boefje_id)
                ooi = self.get_single_ooi(ooi_id)
                self.run_boefje_for_oois(
                    boefje, [ooi], self.request.active_organization, self.api_connector
                )
                return True

        except RequestException as exception:
            messages.add_message(
                self.request, messages.ERROR, f"{action} failed: '{exception}'"
            )

    def get_current_ooi(self) -> OOI:
        # self.ooi is already the current state of the OOI
        if self.get_observed_at().date() == datetime.utcnow().date():
            return self.ooi

        try:
            return self.get_ooi(self.get_ooi_id(), datetime.now(timezone.utc))
        except Http404:
            return None

    def build_breadcrumbs(self) -> List[Breadcrumb]:
        breadcrumbs = super().build_breadcrumbs()
        return breadcrumbs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # List from katalogus
        boefjes = get_enabled_boefjes_for_ooi_class(
            self.ooi.__class__, self.request.active_organization
        )

        context["boefjes"] = boefjes
        context["ooi"] = self.ooi

        declarations, observations, inferences = self.get_origins(
            self.ooi.reference, self.get_observed_at(), self.request.active_organization
        )
        context["declarations"] = declarations
        context["observations"] = observations
        context["inferences"] = inferences

        context["object_details"] = format_display(self.get_ooi_properties(self.ooi))
        context["ooi_types"] = self.get_ooi_types_input_values(self.ooi)
        context["observed_at_form"] = self.get_connector_form()
        context["observed_at"] = self.get_observed_at()
        context["ooi_past_due"] = (
            context["observed_at"].date() < datetime.utcnow().date()
        )
        context["related"] = self.get_related_objects()
        context["ooi_current"] = self.get_current_ooi()
        context["findings_severity_summary"] = self.findings_severity_summary()
        context["severity_summary_totals"] = self.get_findings_severity_totals()
        context["breadcrumbs"] = self.build_breadcrumbs()

        return context
