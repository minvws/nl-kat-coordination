from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from django.contrib import messages
from django.core.paginator import Paginator, Page
from django.http import Http404
from django.shortcuts import redirect
from requests.exceptions import RequestException

from katalogus.client import get_katalogus
from katalogus.utils import get_enabled_boefjes_for_ooi_class
from katalogus.views.mixins import BoefjeMixin
from octopoes.models import OOI
from rocky import scheduler
from rocky.views.mixins import OOIBreadcrumbsMixin
from rocky.views.ooi_detail_related_object import OOIRelatedObjectAddView
from rocky.views.ooi_view import BaseOOIDetailView
from tools.forms.base import ObservedAtForm
from tools.forms.ooi import PossibleBoefjesFilterForm
from tools.models import Indemnification, OrganizationMember
from tools.ooi_helpers import format_display


class PageActions(Enum):
    START_SCAN = "start_scan"


class OOIDetailView(
    BoefjeMixin,
    OOIRelatedObjectAddView,
    BaseOOIDetailView,
    OOIBreadcrumbsMixin,
):
    template_name = "oois/ooi_detail.html"
    connector_form_class = ObservedAtForm
    scan_history_limit = 10

    def post(self, request, *args, **kwargs):
        if not self.indemnification_present:
            messages.add_message(
                request, messages.ERROR, "Indemnification not present at organization %s." % self.organization
            )
            return self.get(request, status_code=403, *args, **kwargs)

        if "action" not in self.request.POST:
            return self.get(request, status_code=404, *args, **kwargs)

        self.ooi = self.get_ooi()

        if not self.handle_page_action(request.POST.get("action")):
            return self.get(request, status_code=500, *args, **kwargs)

        success_message = (
            "Your scan is running successfully in the background. \n "
            "Results will be added to the object list when they are in. "
            "It may take some time, a refresh of the page may be needed to show the results."
        )
        messages.add_message(request, messages.SUCCESS, success_message)

        return redirect("task_list", organization_code=self.organization.code)

    def handle_page_action(self, action: str) -> bool:
        try:
            if action == PageActions.START_SCAN.value:
                boefje_id = self.request.POST.get("boefje_id")
                ooi_id = self.request.GET.get("ooi_id")

                boefje = get_katalogus(self.organization.code).get_boefje(boefje_id)
                ooi = self.get_single_ooi(pk=ooi_id)
                self.run_boefje_for_oois(boefje, [ooi])
                return True

        except RequestException as exception:
            messages.add_message(self.request, messages.ERROR, f"{action} failed: '{exception}'")

    def get_current_ooi(self) -> Optional[OOI]:
        # self.ooi is already the current state of the OOI
        if self.get_observed_at().date() == datetime.utcnow().date():
            return self.ooi

        try:
            return self.get_ooi(pk=self.get_ooi_id(), observed_at=datetime.now(timezone.utc))
        except Http404:
            return None

    def get_organizationmember(self):
        return OrganizationMember.objects.get(user=self.request.user, organization=self.organization)

    def get_organization_indemnification(self):
        return Indemnification.objects.filter(organization=self.organization).exists()

    def get_scan_history(self) -> Page:
        scheduler_id = f"boefje-{self.organization.code}"

        filters = [
            {"field": "data__input_ooi", "operator": "eq", "value": self.get_ooi_id()},
        ]

        # FIXME: in context of ooi detail is doesn't make sense to search
        # for an object name
        if self.request.GET.get("scan_history_search"):
            filters.append(
                {
                    "field": "data__boefje__name",
                    "operator": "eq",
                    "value": self.request.GET.get("scan_history_search"),
                }
            )

        page = int(self.request.GET.get("scan_history_page", 1))

        status = self.request.GET.get("scan_history_status")

        min_created_at = None
        if self.request.GET.get("scan_history_from"):
            min_created_at = datetime.strptime(self.request.GET.get("scan_history_from"), "%Y-%m-%d")

        max_created_at = None
        if self.request.GET.get("scan_history_to"):
            max_created_at = datetime.strptime(self.request.GET.get("scan_history_to"), "%Y-%m-%d")

        scan_history = scheduler.client.get_lazy_task_list(
            scheduler_id=scheduler_id,
            status=status,
            min_created_at=min_created_at,
            max_created_at=max_created_at,
            filters=filters,
        )

        return Paginator(scan_history, self.scan_history_limit).page(page)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        filter_form = PossibleBoefjesFilterForm(self.request.GET)

        # List from katalogus
        boefjes = get_enabled_boefjes_for_ooi_class(self.ooi.__class__, self.organization)

        if boefjes:
            context["enabled_boefjes_available"] = True

        # Filter boefjes on scan level <= OOI clearance level when not "show all"
        # or when not "acknowledged clearance level > 0"
        member = self.get_organizationmember()
        if (
            (filter_form.is_valid() and not filter_form.cleaned_data["show_all"])
            or member.acknowledged_clearance_level <= 0
            or self.get_organization_indemnification()
        ):
            boefjes = [boefje for boefje in boefjes if boefje.scan_level.value <= self.ooi.scan_profile.level]

        context["boefjes"] = boefjes
        context["ooi"] = self.ooi

        declarations, observations, inferences = self.get_origins(
            self.ooi.reference, self.get_observed_at(), self.organization
        )
        context["declarations"] = declarations
        context["observations"] = observations
        context["inferences"] = inferences
        context["member"] = self.get_organizationmember()
        context["object_details"] = format_display(self.get_ooi_properties(self.ooi))
        context["ooi_types"] = self.get_ooi_types_input_values(self.ooi)
        context["observed_at_form"] = self.get_connector_form()
        context["observed_at"] = self.get_observed_at()
        context["ooi_past_due"] = context["observed_at"].date() < datetime.utcnow().date()
        context["related"] = self.get_related_objects()
        context["ooi_current"] = self.get_current_ooi()
        context["findings_severity_summary"] = self.findings_severity_summary()
        context["severity_summary_totals"] = self.get_findings_severity_totals()
        context["possible_boefjes_filter_form"] = filter_form
        context["organization_indemnification"] = self.get_organization_indemnification()
        context["scan_history"] = self.get_scan_history()
        context["scan_history_form_fields"] = [
            "scan_history_from",
            "scan_history_to",
            "scan_history_status",
            "scan_history_search",
            "scan_history_page",
        ]

        return context
