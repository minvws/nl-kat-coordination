import json
from collections import defaultdict
from collections.abc import Iterable, Sequence
from datetime import datetime, timezone
from operator import attrgetter
from typing import Any, Literal, cast
from uuid import uuid4

import structlog
from account.mixins import OrganizationView
from django.conf import settings
from django.contrib import messages
from django.forms import Form
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import urlencode
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from django_weasyprint import WeasyTemplateResponseMixin
from katalogus.client import Boefje, KATalogusError, Plugin, get_katalogus
from pydantic import RootModel, TypeAdapter
from tools.ooi_helpers import create_ooi
from tools.view_helpers import BreadcrumbsMixin, url_with_querystring

from octopoes.models import OOI, Reference
from octopoes.models.ooi.reports import Report as ReportOOI
from reports.forms import OOITypeMultiCheckboxForReportForm
from reports.report_types.concatenated_report.report import ConcatenatedReport
from reports.report_types.definitions import AggregateReport, Report
from reports.report_types.helpers import REPORTS, get_report_by_id, get_report_types_for_oois
from reports.utils import JSONEncoder, debug_json_keys
from rocky.views.mixins import ObservedAtMixin, OOIList
from rocky.views.ooi_view import OOIFilterView

REPORTS_PRE_SELECTION = {
    "clearance_level": ["2", "3", "4"],
    "clearance_type": "declared",
}


def get_selection(request: HttpRequest, pre_selection: dict[str, str | Sequence[str]] | None = None) -> str:
    if pre_selection is not None:
        return "?" + urlencode(pre_selection, True)
    return "?" + urlencode(request.GET, True)


logger = structlog.get_logger(__name__)


class ReportBreadcrumbs(OrganizationView, BreadcrumbsMixin):
    breadcrumbs_step: int = 1

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.breadcrumbs = self.build_breadcrumbs()

    def get_kwargs(self):
        return {"organization_code": self.organization.code}

    def is_valid_breadcrumbs(self):
        return self.breadcrumbs_step < len(self.breadcrumbs)

    def build_breadcrumbs(self):
        kwargs = self.get_kwargs()
        selection = get_selection(self.request)

        breadcrumbs = [
            {
                "url": reverse("reports", kwargs=kwargs) + selection,
                "text": _("Reports"),
            },
        ]

        return breadcrumbs

    def get_breadcrumbs(self):
        if self.is_valid_breadcrumbs():
            return self.breadcrumbs[: self.breadcrumbs_step]
        return self.breadcrumbs

    def get_current(self):
        return self.breadcrumbs[self.breadcrumbs_step - 1]["url"]

    def get_previous(self):
        if self.is_valid_breadcrumbs() and self.breadcrumbs_step >= 2:
            return self.breadcrumbs[self.breadcrumbs_step - 2]["url"]
        return self.get_current()

    def get_next(self):
        if self.is_valid_breadcrumbs():
            return self.breadcrumbs[self.breadcrumbs_step]["url"]
        return self.get_current()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = self.get_breadcrumbs()
        context["next"] = self.get_next()
        context["previous"] = self.get_previous()
        return context


class ReportRecipe:
    def __init__(
        self,
        input_oois: list[str] = [],
        report_types: list[str] = [],
        plugins: dict[str, list[str]] = {},
    ):
        self.input_oois = input_oois
        self.report_types = report_types
        self.plugins = plugins

    def as_json(self):
        return json.dumps(self.__dict__)


class ReportRecipeView(OOIFilterView):
    """
    A recipe is here defined as: all data collected from user selections to create a report.
    The user selects assets (oois) together with the report types and the resulted plugins.
    """

    NONE_OOI_SELECTION_MESSAGE = _("Select at least one OOI to proceed.")
    NONE_REPORT_TYPE_SELECTION_MESSAGE = _("Select at least one report type to proceed.")

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.report_recipe = self.get_report_recipe()

    def get_report_recipe(self) -> ReportRecipe:
        return ReportRecipe(
            self.get_ooi_pks(),
            self.get_report_type_ids(),
            self.get_plugin_ids(),
        )

    def get_ooi_selection(self) -> list[str]:
        selected_oois = self.request.GET.getlist("ooi", [])
        if "all" in selected_oois:
            return selected_oois
        return sorted(set(self.request.POST.getlist("ooi", [])))

    def get_ooi_pks(self) -> list[str]:
        selected_oois = self.get_ooi_selection()
        if "all" in selected_oois:
            return sorted([ooi.primary_key for ooi in self.get_oois()])
        return selected_oois

    def get_oois(self) -> set[type[OOI]]:
        selected_oois = self.get_ooi_selection()
        oois = set()
        if "all" in selected_oois:
            oois = set(
                self.octopoes_api_connector.list_objects(
                    self.get_ooi_types(),
                    valid_time=self.observed_at,
                    limit=OOIList.HARD_LIMIT,
                    scan_level=self.get_ooi_scan_levels(),
                    scan_profile_type=self.get_ooi_profile_types(),
                ).items
            )
        else:
            oois = {self.get_single_ooi(pk=ooi_pk) for ooi_pk in selected_oois}
        return oois

    def get_report_type_ids(self) -> list[str]:
        return sorted(set(self.request.POST.getlist("report_type", [])))

    def get_report_types(self) -> set[type[Report]]:
        return {get_report_by_id(report_type_id) for report_type_id in self.get_report_type_ids()}

    def get_plugins_from_report_type(self) -> dict[str, list[Plugin]]:
        """
        Returns plugins from KAT-alogus from the selected report types.
        """

        report_types = self.get_report_types()
        plugins: dict[str, Any] = {"required": [], "optional": []}

        for report_type in report_types:
            for required_optional, report_type_plugin_ids in report_type.plugins.items():
                plugins[required_optional] += report_type_plugin_ids

        # remove duplicate plugins
        plugins = {required_optional: set(plugin_ids) for required_optional, plugin_ids in plugins.items()}

        # remove optional plugins that is also in the set of required plugins
        for plugin_id in plugins["required"]:
            if plugin_id in plugins["optional"]:
                plugins["optional"].remove(plugin_id)

        # Finally we can get the plugins from KAT-alogus with the set of plugin ids and sort them by name and ascending.
        try:
            return {
                required_optional: sorted(
                    get_katalogus(self.organization.code).get_plugins(ids=list(plugin_ids)), key=attrgetter("name")
                )
                for required_optional, plugin_ids in plugins.items()
                if plugin_ids
            }
        except KATalogusError as error:
            messages.error(self.request, error.message)
            return {}

    def get_plugin_ids(self) -> dict[str, list[str]]:
        report_type_plugins = self.get_plugins_from_report_type()
        plugin_ids: dict[str, list[str]] = {"required": [], "optional": []}
        for required_optional, plugins in report_type_plugins.items():
            plugin_ids[required_optional] = [plugin.id for plugin in plugins]
        return plugin_ids

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["report_recipe"] = self.report_recipe
        return context


class OOISelectionView(ReportRecipeView):
    """
    Shows a list of OOIs to select from and handles OOIs selection requests.
    """

    def get_ooi_filter_forms(self, ooi_types: Iterable[type[OOI]]) -> dict[str, Form]:
        return {
            "ooi_type_form": OOITypeMultiCheckboxForReportForm(
                sorted([ooi_class.get_ooi_type() for ooi_class in ooi_types]),
                self.request.GET,
            )
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["selected_oois"] = self.get_ooi_selection()
        context.update(self.get_ooi_filter_forms(self.ooi_types))
        return context


class ReportTypeSelectionView(ReportRecipeView):
    """
    Shows report types and handles selections and requests.
    """

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.show_report_types = get_report_types_for_oois(self.get_ooi_pks())

    def get_report_types_from_ooi_selelection(self) -> list[dict[str, str]]:
        """
        The report types are fetched from which ooi is selected. Shows all report types for the oois.
        """

        report_types = [
            {
                "id": report_type.id,
                "name": report_type.name,
                "description": report_type.description,
                "label_style": report_type.label_style,
            }
            for report_type in self.show_report_types
        ]
        return report_types

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["total_oois"] = len(self.report_recipe.input_oois)
        context["oois"] = self.get_oois()
        context["available_report_types"] = self.get_report_types_from_ooi_selelection()
        return context


class ReportPluginView(ReportRecipeView):
    """
    This view shows the required and optional plugins together with the summary per report type.
    """

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.plugins = self.get_plugins_from_report_type()

    def plugins_enabled(self) -> dict[str, bool]:
        enabled_plugins_data: dict[str, bool] = {"required": False, "optional": False}
        enabled_plugins = []

        for required_optional, plugins in self.plugins.items():
            for plugin in plugins:
                enabled_plugins.append(plugin.enabled)
            enabled_plugins_data[required_optional] = all(enabled_plugins)
        return enabled_plugins_data

    def get_plugin_data(self):
        report_types: dict[str, Any] = {}
        plugin_report_types: dict[str, list] = {}
        total_enabled_plugins = {"required": 0, "optional": 0}
        total_available_plugins = {"required": 0, "optional": 0}

        if self.plugins:
            for report_type in self.get_report_types():
                for plugin_type in ["required", "optional"]:
                    # Mypy doesn't infer this automatically https://github.com/python/mypy/issues/9168
                    plugin_type = cast(Literal["required", "optional"], plugin_type)
                    number_of_enabled = sum(
                        (1 if plugin.enabled and plugin.id in report_type.plugins[plugin_type] else 0)
                        for plugin in self.plugins[plugin_type]
                    )
                    report_plugins = report_type.plugins[plugin_type]

                    for plugin in report_plugins:
                        if plugin not in plugin_report_types:
                            plugin_report_types[plugin] = [
                                {
                                    "name": report_type.name,
                                    "label_style": report_type.label_style,
                                }
                            ]
                        else:
                            plugin_report_types[plugin].append(
                                {
                                    "name": report_type.name,
                                    "label_style": report_type.label_style,
                                }
                            )

                    total_enabled_plugins[plugin_type] += number_of_enabled
                    total_available_plugins[plugin_type] += len(report_plugins)

                    if report_type.name not in report_types:
                        report_types[report_type.name] = {}

                    report_types[report_type.name][f"number_of_enabled_{plugin_type}"] = number_of_enabled
                    report_types[report_type.name][f"number_of_available_{plugin_type}"] = len(report_plugins)

        plugin_data = {
            "total_enabled_plugins": total_enabled_plugins,
            "total_available_plugins": total_available_plugins,
            "report_types": report_types,
            "plugin_report_types": plugin_report_types,
        }

        return plugin_data

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["created_at"] = datetime.now()
        context["enabled_plugins"] = self.plugins_enabled()
        context["plugin_data"] = self.get_plugin_data()
        context["plugins"] = self.plugins
        return context


class ReportFinalSettingsView(ReportRecipeView):
    def get_plugin_data_for_saving(self) -> list[dict]:
        plugin_data = []
        report_type_plugins = self.get_plugins_from_report_type()
        for required_optional, plugins in report_type_plugins.items():
            for plugin in plugins:
                plugin_data.append(
                    {
                        "required": required_optional == "required",
                        "enabled": plugin.enabled,
                        "name": plugin.name,
                        "scan_level": plugin.scan_level.value if isinstance(plugin, Boefje) else 0,
                        "type": plugin.type,
                        "description": plugin.description,
                    }
                )

        return plugin_data

    @staticmethod
    def finalise_report_names(report_names: list[str], reference_dates: list[str]) -> list[str]:
        final_report_names = []

        if len(report_names) == len(reference_dates):
            for index, report_name in enumerate(report_names):
                date_format = ""
                if reference_dates[index] and reference_dates[index] != "":
                    date_format = " - "
                    if reference_dates[index] == "week":
                        date_format += _("Week %W, %Y")
                    else:
                        date_format += reference_dates[index]
                final_report_name = f"{report_name} {date_format}".strip()
                final_report_names.append(final_report_name)
        if not final_report_names:
            return report_names
        return final_report_names

    def save_report_raw(self, data: dict) -> str:
        report_data_raw_id = self.bytes_client.upload_raw(
            raw=ReportDataDict(data).model_dump_json().encode(),
            manual_mime_types={"openkat/report"},
        )

        return report_data_raw_id

    def save_report_ooi(
        self,
        report_data_raw_id: str,
        report_type: type[Report],
        input_oois: list[str],
        parent: Reference | None,
        has_parent: bool,
        observed_at: datetime,
        name: str,
    ) -> ReportOOI:
        if not name or name.isspace():
            name = report_type.name
        report_ooi = ReportOOI(
            name=str(name),
            report_type=str(report_type.id),
            template=report_type.template_path,
            report_id=uuid4(),
            organization_code=self.organization.code,
            organization_name=self.organization.name,
            organization_tags=list(self.organization.tags.all()),
            data_raw_id=report_data_raw_id,
            date_generated=datetime.now(timezone.utc),
            input_oois=input_oois,
            observed_at=observed_at,
            parent_report=parent,
            has_parent=has_parent,
        )

        create_ooi(
            api_connector=self.octopoes_api_connector,
            bytes_client=self.bytes_client,
            ooi=report_ooi,
            observed_at=observed_at,
        )

        return report_ooi

    def get_observed_at(self):
        return self.observed_at if self.observed_at < datetime.now(timezone.utc) else datetime.now(timezone.utc)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["created_at"] = datetime.now()
        return context


class ReportsLandingView(ReportBreadcrumbs, TemplateView):
    """
    Landing page for Reports.
    """

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return redirect(reverse("report_history", kwargs=self.get_kwargs()))


class ReportDataDict(RootModel):
    root: Any

    class Config:
        arbitrary_types_allowed = True


def recursive_dict():
    return defaultdict(recursive_dict)


class ViewReportView(ObservedAtMixin, OrganizationView, TemplateView):
    """
    This will display reports using report_id from reports history.
    Will fetch Report OOI and recreate report with data saved in bytes.
    """

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.report_id = request.GET.get("report_id")
        self.report_ooi = self.octopoes_api_connector.get(
            Reference.from_str(f"{self.report_id}"), valid_time=self.observed_at
        )

    def get(self, request, *args, **kwargs):
        if "json" in self.request.GET and self.request.GET["json"] == "true":
            self.bytes_client.login()
            data = json.loads(self.bytes_client.get_raw(raw_id=self.report_ooi.data_raw_id))

            response = {
                "organization_code": self.organization.code,
                "organization_name": self.organization.name,
                "organization_tags": list(self.organization.tags.all()),
                "data": {
                    "report_data": {},
                    "post_processed_data": data,
                },
            }

            try:
                response = JsonResponse(response, encoder=JSONEncoder)
            except TypeError:
                # We can't use translated strings as keys in JSON. This
                # debugging code makes it easy to spot where the problem is.
                if settings.DEBUG:
                    debug_json_keys(data, [])
                raise
            else:
                response["Content-Disposition"] = f"attachment; filename=report-{self.organization.code}.json"
                return response

        return super().get(request, *args, **kwargs)

    def get_template_names(self):
        if self.report_ooi.report_type and issubclass(get_report_by_id(self.report_ooi.report_type), AggregateReport):
            return [
                "aggregate_report.html",
            ]
        else:
            return [
                "generate_report.html",
            ]

    def get_children_reports(self) -> list[ReportOOI]:
        return self.octopoes_api_connector.query(
            "Report.<parent_report[is Report]",
            valid_time=self.observed_at,
            source=self.report_ooi.reference,
        )

    @staticmethod
    def get_report_types(reports: list[ReportOOI]) -> list[dict[str, Any]]:
        return [report.class_attributes() for report in {get_report_by_id(report.report_type) for report in reports}]

    def get_report_data_from_bytes(self, report: ReportOOI) -> dict[str, Any]:
        return TypeAdapter(Any, config={"arbitrary_types_allowed": True}).validate_json(
            self.bytes_client.get_raw(raw_id=report.data_raw_id)
        )

    def get_input_oois(self, reports: list[ReportOOI]) -> list[OOI]:
        ooi_pks = {ooi for report in reports for ooi in report.input_oois}

        return [
            self.octopoes_api_connector.get(Reference.from_str(ooi), valid_time=self.observed_at) for ooi in ooi_pks
        ]

    def get_context_data(self, **kwargs):
        # TODO: add config and plugins
        # TODO: add template OOI
        context = super().get_context_data(**kwargs)

        self.bytes_client.login()
        report_data: dict[str, dict[str, dict[str, Any]]] = {}

        children_reports = [
            child for x in REPORTS for child in self.get_children_reports() if child.report_type == x.id
        ]
        report_types: list[dict[str, Any]] = []

        if issubclass(
            get_report_by_id(self.report_ooi.report_type), ConcatenatedReport
        ):  # get single reports data (children's)
            context["data"] = self.get_report_data_from_bytes(self.report_ooi)
            for report in children_reports:
                for ooi in report.input_oois:
                    report_data.setdefault(report.report_type, {})[ooi] = {
                        "data": self.get_report_data_from_bytes(report)["report_data"],
                        "template": report.template,
                        "report_name": report.name,
                    }

            input_oois = self.get_input_oois(children_reports)
            report_types = self.get_report_types(children_reports)

        elif issubclass(get_report_by_id(self.report_ooi.report_type), AggregateReport):  # its an aggregate report
            context["post_processed_data"] = self.get_report_data_from_bytes(self.report_ooi)
            input_oois = self.get_input_oois([self.report_ooi])
            report_types = self.get_report_types(children_reports)

        else:
            # its a single report
            report_data[self.report_ooi.report_type] = {}
            context["data"] = self.get_report_data_from_bytes(self.report_ooi)
            for ooi in self.report_ooi.input_oois:
                report_data[self.report_ooi.report_type][ooi] = {
                    "data": context["data"]["report_data"],
                    "template": self.report_ooi.template,
                    "report_name": self.report_ooi.name,
                }

            input_oois = self.get_input_oois([self.report_ooi])
            report_types = self.get_report_types([self.report_ooi])

        context["report_data"] = report_data
        context["report_name"] = self.report_ooi.name
        context["report_types"] = [
            report_type for x in REPORTS for report_type in report_types if report_type["id"] == x.id
        ]
        context["created_at"] = self.report_ooi.date_generated
        context["observed_at"] = self.report_ooi.observed_at
        context["total_oois"] = len(input_oois)
        context["oois"] = input_oois

        context["template"] = self.report_ooi.template
        context["report_download_pdf_url"] = url_with_querystring(
            reverse(
                "view_report_pdf",
                kwargs={"organization_code": self.organization.code},
            ),
            True,
            **self.request.GET,
        )
        context["report_download_json_url"] = url_with_querystring(
            reverse(
                "view_report",
                kwargs={"organization_code": self.organization.code},
            ),
            True,
            **dict(json="true", **self.request.GET),
        )

        return context


class ViewReportPDFView(ViewReportView, WeasyTemplateResponseMixin):
    pdf_filename = "report.pdf"
    pdf_attachment = False
    pdf_options = {
        "pdf_variant": "pdf/ua-1",
    }

    def get_template_names(self):
        if self.report_ooi.report_type and issubclass(get_report_by_id(self.report_ooi.report_type), AggregateReport):
            return [
                "aggregate_report_pdf.html",
            ]
        else:
            return [
                "generate_report_pdf.html",
            ]
