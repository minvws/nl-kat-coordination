from datetime import datetime
from logging import getLogger
from typing import Any, Dict, List, Optional, Set, Type, Union

from account.mixins import OrganizationView
from django.contrib import messages
from django.forms import Form
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import urlencode
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from katalogus.client import Plugin, get_katalogus
from tools.view_helpers import BreadcrumbsMixin

from octopoes.models import OOI
from octopoes.models.types import OOIType
from reports.forms import OOITypeMultiCheckboxForReportForm
from reports.report_types.definitions import Report, ReportType
from reports.report_types.helpers import get_plugins_for_report_ids, get_report_by_id
from rocky.views.mixins import OctopoesView

logger = getLogger(__name__)


class ReportBreadcrumbs(OrganizationView, BreadcrumbsMixin):
    current_step: int = 1

    def get_selection(self, pre_selection: Optional[Dict[str, Union[str, List[str]]]] = None) -> str:
        if pre_selection:
            return "?" + urlencode(pre_selection, True)
        return "?" + urlencode(self.request.GET, True)

    def get_kwargs(self):
        return {"organization_code": self.organization.code}

    def build_breadcrumbs(self):
        kwargs = self.get_kwargs()
        selection = self.get_selection()

        breadcrumbs = [
            {
                "url": reverse("reports", kwargs=kwargs) + selection,
                "text": _("Reports"),
            },
        ]

        return breadcrumbs

    def get_current(self):
        return self.build_breadcrumbs()[: self.current_step]

    def get_previous(self):
        return self.build_breadcrumbs()[self.current_step - 2]["url"]

    def get_next(self):
        breadcrumbs = self.build_breadcrumbs()
        if self.current_step < len(breadcrumbs):
            return breadcrumbs[self.current_step]["url"]
        return breadcrumbs[self.current_step - 1]["url"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = self.get_current()
        context["next"] = self.get_next()
        context["previous"] = self.get_previous()
        return context


class BaseReportView(OctopoesView):
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.valid_time = self.get_observed_at()
        self.selected_oois = request.GET.getlist("ooi", [])
        self.selected_report_types = request.GET.getlist("report_type", [])

        self.report_types = self.get_report_types_from_choice()
        report_ids = [report.id for report in self.report_types]
        self.plugins = self.get_required_optional_plugins(get_plugins_for_report_ids(report_ids))

    def get_oois(self) -> List[OOI]:
        oois = []
        for ooi_id in self.selected_oois:
            try:
                oois.append(self.get_single_ooi(ooi_id))
            except Exception:
                logger.warning("No data could be found for '%s' ", ooi_id)
        return oois

    def get_ooi_filter_forms(self, ooi_types: Set[OOIType]) -> Dict[str, Form]:
        return {
            "ooi_type_form": OOITypeMultiCheckboxForReportForm(
                sorted([ooi_class.get_ooi_type() for ooi_class in ooi_types]), self.request.GET
            )
        }

    def get_report_types_for_generate_report(self, reports: Set[Type[Report]]) -> List[Dict[str, str]]:
        return [
            {"id": report_type.id, "name": report_type.name, "description": report_type.description}
            for report_type in reports
        ]

    def get_report_types_for_aggregate_report(
        self, reports_dict: Dict[str, Set[Type[Report]]]
    ) -> Dict[str, List[Dict[str, str]]]:
        report_types = {}
        for option, reports in reports_dict.items():
            report_types[option] = self.get_report_types_for_generate_report(reports)
        return report_types

    def get_required_optional_plugins(self, plugin_ids: Dict[str, Set[str]]) -> Dict[str, Plugin]:
        plugins = {}
        for plugin, plugin_ids in plugin_ids.items():
            plugins[plugin] = [get_katalogus(self.organization.code).get_plugin(plugin_id) for plugin_id in plugin_ids]

        for plugin_type, plugin_list in plugins.items():
            if all(plugin.enabled for plugin in plugin_list):
                plugins[plugin_type] = []

        return plugins

    def are_plugins_enabled(self, plugins_dict: Dict[str, Plugin]) -> bool:
        for k, plugins in plugins_dict.items():
            for plugin in plugins:
                if not plugin.enabled:
                    return False
        return True

    def get_report_types_from_choice(self) -> List[Type[Report]]:
        report_types = []
        for report_type in self.selected_report_types:
            try:
                report = get_report_by_id(report_type)
                report_types.append(report)
            except ValueError:
                error_message = _("Report type '%s' does not exist.") % report_type
                messages.add_message(self.request, messages.ERROR, error_message)
                pass
        return report_types

    def get_report_types(self) -> List[ReportType]:
        return [
            {"id": report_type.id, "name": report_type.name, "description": report_type.description}
            for report_type in self.get_report_types_from_choice()
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["observed_at"] = self.valid_time
        context["created_at"] = datetime.now()
        context["selected_oois"] = self.selected_oois
        context["selected_report_types"] = self.selected_report_types
        context["plugins"] = self.plugins
        context["oois"] = self.get_oois()
        return context


class ReportsLandingView(ReportBreadcrumbs, TemplateView):
    """
    Landing page for Reports.
    """

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return redirect(reverse("generate_report_landing", kwargs=self.get_kwargs()))
