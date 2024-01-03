from typing import Any, Dict, List, Optional, Set, Type, Union

from account.mixins import OrganizationView
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
from reports.report_types.helpers import get_report_by_id
from rocky.views.mixins import OOIList
from rocky.views.ooi_view import OOIFilterView


class ReportBreadcrumbs(OrganizationView, BreadcrumbsMixin):
    current_step: int = 1

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


class BaseReportView(OOIFilterView):
    pre_selection: Optional[Dict[str, Union[str, List[str]]]] = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.selected_oois = request.GET.getlist("ooi", [])
        self.selected_report_types = request.GET.getlist("report_type", [])

    def get_selection(self) -> str:
        if self.pre_selection is not None:
            return "?" + urlencode(self.pre_selection, True)
        return "?" + urlencode(self.request.GET, True)

    def get_oois(self) -> List[OOI]:
        if "all" in self.selected_oois:
            return self.octopoes_api_connector.list(
                self.get_ooi_types(),
                valid_time=self.valid_time,
                limit=OOIList.HARD_LIMIT,
                scan_level=self.get_ooi_scan_levels(),
                scan_profile_type=self.get_ooi_profile_types(),
            ).items
        return [self.get_single_ooi(ooi_id) for ooi_id in self.selected_oois]

    def get_pk_oois(self) -> List[str]:
        if "all" in self.selected_oois:
            return [ooi.primary_key for ooi in self.get_oois()]
        return self.selected_oois

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
        return plugins

    def are_plugins_enabled(self, plugins_dict: Dict[str, Plugin]) -> bool:
        enabled_plugins = []
        for k, plugins in plugins_dict.items():
            for plugin in plugins:
                enabled_plugins.append(plugin.enabled)
        return all(enabled_plugins)

    def get_report_types_from_choice(self) -> List[Type[Report]]:
        return [get_report_by_id(report_type) for report_type in self.selected_report_types]

    def get_report_types(self) -> List[ReportType]:
        return [
            {"id": report_type.id, "name": report_type.name, "description": report_type.description}
            for report_type in self.get_report_types_from_choice()
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["selected_oois"] = self.selected_oois
        context["selected_report_types"] = self.selected_report_types
        context["selection"] = self.get_selection()
        return context


class ReportsLandingView(ReportBreadcrumbs, TemplateView):
    """
    Landing page for Reports.
    """

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return redirect(reverse("generate_report_landing", kwargs=self.get_kwargs()))
