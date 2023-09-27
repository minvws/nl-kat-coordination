from logging import getLogger

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from katalogus.client import get_katalogus
from tools.view_helpers import BreadcrumbsMixin

from octopoes.models import Reference
from reports.forms import OOITypeMultiCheckboxForReportForm
from reports.report_types.helpers import (
    get_ooi_types_with_report,
    get_plugins_for_report_ids,
    get_report_by_id,
    get_report_types_for_oois,
)
from rocky.views.mixins import OctopoesView
from rocky.views.ooi_view import BaseOOIListView

logger = getLogger(__name__)


class ReportBreadcrumbs(BreadcrumbsMixin):
    current_step: int = 0

    def build_breadcrumbs(self):
        kwargs = {"organization_code": self.organization.code}
        breadcrumbs = [
            {
                "url": reverse("report_oois_selection", kwargs=kwargs),
                "text": _("Reports"),
            },
            {
                "url": reverse("report_type_selection", kwargs=kwargs),
                "text": _("Choose report types"),
            },
            {
                "url": reverse("report_setup_scan", kwargs=kwargs),
                "text": _("Set up scan"),
            },
            {
                "url": reverse("report_view", kwargs=kwargs),
                "text": _("View Report"),
            },
        ]

        return breadcrumbs[: self.current_step]


class BaseReportView(ReportBreadcrumbs, OctopoesView):
    ooi_types = get_ooi_types_with_report()

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.ooi_selection = request.GET.getlist("ooi", [])
        self.report_types_selection = request.GET.getlist("report_type", [])
        self.katalogus_client = get_katalogus(self.organization.code)

    def get_report_types(self):
        return [
            {"id": report_type.id, "name": report_type.name, "description": report_type.description}
            for report_type in get_report_types_for_oois(self.ooi_selection)
        ]

    def get_reports_data(self):
        report_data = {}
        if self.ooi_selection and self.report_types_selection:
            for ooi in self.ooi_selection:
                for report in self.report_types_selection:
                    report = get_report_by_id(report)
                    if Reference.from_str(ooi).class_type in report.input_ooi_types:
                        data, template = report(self.octopoes_api_connector).generate_data(ooi)
                        report_data[f"{report.name}|{str(ooi)}"] = {"data": data, "template": template}
        return report_data

    def get_required_optional_plugins(self):
        plugins = get_plugins_for_report_ids(self.report_types_selection)
        for plugin, value in plugins.items():
            plugins[plugin] = [self.katalogus_client.get_plugin(plugin_id) for plugin_id in value]
        return plugins

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["oois"] = self.ooi_selection
        context["report_types"] = self.get_report_types()
        context["ooi_type_form"] = OOITypeMultiCheckboxForReportForm(self.request.GET)
        if self.report_types_selection:
            context["plugins"] = self.get_required_optional_plugins()
        context["report_data"] = self.get_reports_data()
        return context


class ReportOOISelectionView(BaseReportView, BaseOOIListView):
    """
    Select OOIs from list to include in report.
    """

    template_name = "report_oois_selection.html"
    current_step = 1


class ReportTypeSelectionView(BaseReportView, TemplateView):
    """
    Shows all possible report types from a list of OOIs.
    Chooses report types to generate a report.
    """

    template_name = "report_type_selection.html"
    current_step = 2

    def get(self, request, *args, **kwargs):
        if not self.ooi_selection:
            messages.add_message(self.request, messages.ERROR, _("Select at least one OOI to proceed."))
            return redirect(reverse("report_oois_selection", kwargs={"organization_code": self.organization.code}))
        return super().get(request, *args, **kwargs)


class ReportSetupScanView(BaseReportView, TemplateView):
    """
    Show required and optional plugins to start scans to generate OOIs to include in report.
    """

    template_name = "report_setup_scan.html"
    current_step = 3


class ReportView(BaseReportView, TemplateView):
    """
    Shows the report generated from OOIS and report types.
    """

    template_name = "report.html"
    current_step = 4
