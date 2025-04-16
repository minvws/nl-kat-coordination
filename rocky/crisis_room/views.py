import json
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode
from uuid import UUID

import structlog
from account.mixins import OrganizationView
from django.conf import settings
from django.contrib import messages
from django.db import IntegrityError
from django.db.models.manager import BaseManager
from django.http import HttpResponse
from django.http.request import HttpRequest
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView
from django.views.generic.edit import FormView
from httpx import HTTPStatusError
from reports.report_types.findings_report.report import SEVERITY_OPTIONS
from tools.forms.ooi_form import _EXCLUDED_OOI_TYPES
from tools.models import Organization, OrganizationMember

from crisis_room.forms import AddDashboardForm, ObjectListSettingsForm
from crisis_room.management.commands.dashboards import (
    FINDINGS_DASHBOARD_NAME,
    delete_dashboard,
    get_or_create_dashboard,
    get_or_create_dashboard_data,
)
from crisis_room.models import Dashboard, DashboardData
from octopoes.config.settings import DEFAULT_SCAN_LEVEL_FILTER, DEFAULT_SCAN_PROFILE_TYPE_FILTER
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import ScanLevel, ScanProfileType
from octopoes.models.exception import ObjectNotFoundException
from octopoes.models.ooi.reports import HydratedReport
from octopoes.models.types import get_collapsed_types, type_by_name
from rocky.bytes_client import get_bytes_client

logger = structlog.get_logger(__name__)


class DashboardItem:
    item: DashboardData | None = None
    data: dict[str, Any] = {}


class DashboardService:
    @staticmethod
    def get_organizations_findings(report_data: dict[str, Any]) -> dict[str, Any]:
        findings = {}
        highest_risk_level = ""
        if "findings" in report_data and report_data["findings"] and report_data["findings"]["finding_types"]:
            finding_types = report_data["findings"]["finding_types"]
            highest_risk_level = finding_types[0]["finding_type"]["risk_severity"]
            critical_high_finding_types = list(
                filter(
                    lambda finding_type: finding_type["finding_type"]["risk_severity"] == "critical"
                    or finding_type["finding_type"]["risk_severity"] == "high",
                    finding_types,
                )
            )
            report_data["findings"]["finding_types"] = critical_high_finding_types[:25]

        findings = report_data | {"highest_risk_level": highest_risk_level}
        return findings

    def get_reports(self, valid_time: datetime, report_filters: list[tuple[str, str]]) -> dict[UUID, HydratedReport]:
        """
        Returns for each recipe ID query'ed, the latest (valid_time) HydratedReport.
        """

        if report_filters:
            org_code, _ = report_filters[0]
            # We need at least 1 org connector to fetch reports from all other orgs.
            connector = OctopoesAPIConnector(
                settings.OCTOPOES_API, org_code, timeout=settings.ROCKY_OUTGOING_REQUEST_TIMEOUT
            )
            try:
                return connector.bulk_list_reports(valid_time, report_filters)
            except (HTTPStatusError, ObjectNotFoundException):
                return {}
        return {}

    @staticmethod
    def get_report_bytes_data(raw_ids: list[str]) -> dict[str, dict[str, Any]]:
        """
        Return for each raw id key its bytes content value across all member organizations.
        """
        # When organization is None, data is fetched across all organizations.
        bytes_client = get_bytes_client(None)
        bytes_client.login()
        try:
            return bytes_client.get_raws_all(raw_ids)
        except (HTTPStatusError, ObjectNotFoundException):
            return {}

    def get_dashboard_items(self, dashboards_data: BaseManager[DashboardData]) -> list[DashboardItem]:
        dashboard_items: list[DashboardItem] = []

        recipes_data = {}
        reports_data = {}

        raw_ids = []
        report_filters = []

        # First collect al data, if recipe id is found then fetch recipe ids to get reports later.
        for dashboard_data in dashboards_data:
            if not dashboard_data.recipe and dashboard_data.query_from == "object_list":
                dashboard_item = DashboardItem()
                dashboard_item.item = dashboard_data
                dashboard_item.data = self.get_ooi_list(dashboard_data)
                dashboard_items.append(dashboard_item)

            if dashboard_data.recipe:
                report_filters.append((dashboard_data.dashboard.organization.code, str(dashboard_data.recipe)))
                recipes_data[dashboard_data] = dashboard_data.recipe

        if recipes_data:
            # Returns for each recipe id its Hydrated report.
            reports: dict[UUID, HydratedReport] = self.get_reports(datetime.now(timezone.utc), report_filters)

            # After reports are collected, collect data raw ids to fetch data from Bytes later.
            for dashboard_data, recipe_id in recipes_data.items():
                try:
                    hydrated_report = reports[recipe_id]
                    raw_ids.append(hydrated_report.data_raw_id)
                    reports_data[dashboard_data] = hydrated_report
                except KeyError:
                    continue

            # Get report data from bytes, per data raw id its report data
            report_data_from_bytes: dict[str, dict[str, Any]] = self.get_report_bytes_data(raw_ids)

            # Finally merge all data necessary to show dashboard data
            for dashboard_data, hydrated_report in reports_data.items():
                dashboard_item = DashboardItem()
                dashboard_item.item = dashboard_data
                dashboard_item.data = {"report": hydrated_report}

                try:
                    report_data = report_data_from_bytes[hydrated_report.data_raw_id]

                    if dashboard_data.findings_dashboard:
                        report_data = self.get_organizations_findings(report_data)

                    dashboard_item.data.update({"report_data": report_data})
                    dashboard_items.append(dashboard_item)
                except KeyError:
                    continue

        return dashboard_items

    @staticmethod
    def get_organizations_findings_summary(organizations_findings: list[DashboardItem]) -> dict[str, Any]:
        summary: dict[str, Any] = {
            "total_by_severity_per_finding_type": {severity: 0 for severity in SEVERITY_OPTIONS},
            "total_by_severity": {severity: 0 for severity in SEVERITY_OPTIONS},
            "total_finding_types": 0,
            "total_occurrences": 0,
        }

        summary_added = False

        for findings in organizations_findings:
            if "findings" in findings.data["report_data"] and "summary" in findings.data["report_data"]["findings"]:
                for summary_item, data in findings.data["report_data"]["findings"]["summary"].items():
                    if isinstance(data, dict):
                        for severity, total in data.items():
                            summary[summary_item][severity] += total
                            summary_added = True
                    else:
                        summary[summary_item] += data
                        summary_added = True

        if not summary_added:
            return {}

        return summary

    def get_dashboard_navigation(self, organization):
        dashboard_names = []
        dashboards = Dashboard.objects.filter(organization=organization)
        for dashboard in dashboards:
            dashboard_names.append(dashboard.name)
        return list(set(dashboard_names))

    def get_ooi_list(self, dashboard_data):
        query = json.loads(dashboard_data.query)
        ooi_list = []

        all_oois = {
            ooi_class for ooi_class in get_collapsed_types() if ooi_class.get_ooi_type() not in _EXCLUDED_OOI_TYPES
        }
        all_scan_levels = DEFAULT_SCAN_LEVEL_FILTER
        all_scan_profile_types = DEFAULT_SCAN_PROFILE_TYPE_FILTER

        ooi_types = (
            {type_by_name(t) for t in query["ooi_types"] if t not in _EXCLUDED_OOI_TYPES}
            if query["ooi_types"]
            else all_oois
        )
        scan_level = {ScanLevel(int(cl)) for cl in query["scan_level"]} if query["scan_level"] else all_scan_levels
        scan_profile_type = (
            {ScanProfileType(ct) for ct in query["scan_profile_type"]}
            if query["scan_profile_type"]
            else all_scan_profile_types
        )

        octopoes_client = OctopoesAPIConnector(
            settings.OCTOPOES_API,
            dashboard_data.dashboard.organization.code,
            timeout=settings.ROCKY_OUTGOING_REQUEST_TIMEOUT,
        )

        ooi_list = octopoes_client.list_objects(
            ooi_types,
            valid_time=datetime.now(timezone.utc),
            limit=query["limit"],
            scan_level=scan_level,
            scan_profile_type=scan_profile_type,
            search_string=query["search_string"],
            order_by=query["order_by"],
            asc_desc=query["asc_desc"],
        ).items

        return ooi_list


class CrisisRoomView(TemplateView):
    """This is the Crisis Room for all organizations."""

    template_name = "crisis_room.html"

    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs)

        dashboard_service = DashboardService()
        organizations = self.get_user_organizations()

        dashboards_data = DashboardData.objects.filter(
            dashboard__name=FINDINGS_DASHBOARD_NAME, dashboard__organization__in=organizations, findings_dashboard=True
        )

        self.organizations_findings = dashboard_service.get_dashboard_items(dashboards_data)
        self.organizations_findings_summary = dashboard_service.get_organizations_findings_summary(
            self.organizations_findings
        )

    def get_user_organizations(self) -> list[Organization]:
        return [member.organization for member in OrganizationMember.objects.filter(user=self.request.user)]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"url": reverse("crisis_room"), "text": "Crisis Room"}]
        context["dashboard_items"] = self.organizations_findings
        context["organizations_findings_summary"] = self.organizations_findings_summary
        return context


class OrganizationsCrisisRoomView(TemplateView, OrganizationView):
    """This is the Crisis Room for a single organization."""

    template_name = "organization_crisis_room.html"
    dashboard_service = DashboardService()

    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs)

        # Default is the findings dashboard
        dashboard_name = self.request.GET.get("dashboard", FINDINGS_DASHBOARD_NAME)
        self.dashboard = Dashboard.objects.get(organization=self.organization, name=dashboard_name)
        dashboards_data = DashboardData.objects.filter(dashboard=self.dashboard, display_in_dashboard=True)
        self.dashboard_items = self.dashboard_service.get_dashboard_items(dashboards_data)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["all_dashboard_names"] = self.dashboard_service.get_dashboard_navigation(self.organization)
        context["dashboard"] = self.dashboard
        context["dashboard_items"] = self.dashboard_items
        context["add_dashboard_form"] = AddDashboardForm
        context["breadcrumbs"] = [
            {
                "url": reverse("organization_crisis_room", kwargs={"organization_code": self.organization.code}),
                "text": "Crisis Room",
            }
        ]
        return context


class DeleteDashboardView(OrganizationView):
    """Delete the selected dashboard."""

    def get(self, request, *args, **kwargs) -> HttpResponse:
        dashboard_name = request.GET.get("dashboard")
        dashboard = Dashboard.objects.get(organization=self.organization, name=dashboard_name)
        deleted, _ = delete_dashboard(dashboard)

        if deleted:
            query_params = "?" + urlencode({"dashboard": dashboard_name})
            messages.success(request, f"Dashboard '{dashboard_name}' has been deleted.")
        else:
            messages.error(request, f"Dashboard '{dashboard_name}' could not be deleted.")

        return redirect(
            reverse("organization_crisis_room", kwargs={"organization_code": self.organization.code})
            + "?"
            + query_params
        )


class AddDashboardView(OrganizationView, FormView):
    """Add a new dashboard tab to the organization."""

    template_name = "organization_crisis_room.html"
    form_class = AddDashboardForm

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Create a new dashboard tab."""
        form = self.get_form()
        if form.is_valid():
            dashboard_name = request.POST.get("dashboard_name")
            try:
                dashboard, created = get_or_create_dashboard(dashboard_name, self.organization)
                if created:
                    messages.success(request, f"Dashboard '{dashboard.name}' has been created.")
                else:
                    messages.error(request, f"Dashboard with name '{dashboard.name}' already exists.")

            except IntegrityError:
                messages.error(request, "Dashboard could not be created.")

            query_params = urlencode({"dashboard": dashboard.name})
            return redirect(
                reverse("organization_crisis_room", kwargs={"organization_code": self.organization.code})
                + "?"
                + query_params
            )
        else:
            return self.form_invalid(form)


class AddDashboardItemView(OrganizationView, FormView):
    """Add a new dashboard item to the selected dashboard."""

    form_class = ObjectListSettingsForm
    template_name = "oois/ooi_list.html"

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        form = self.get_form()
        if form.is_valid():
            form_data = form.cleaned_data
            query_from = request.POST.get("query_from")

            if query_from == "object_list":
                template = "partials/dashboard_ooi_list.html"
                sort_by = form_data["order_by"].split("-")
                query = {
                    "ooi_types": request.POST.getlist("ooi_type"),
                    "scan_level": request.POST.getlist("clearance_level"),
                    "scan_profile_type": request.POST.getlist("clearance_type"),
                    "search_string": request.POST.get("search_string"),
                    "order_by": sort_by[0],
                    "asc_desc": sort_by[1],
                    "limit": int(form_data["limit"]),
                }
            else:
                template = request.POST.get("template")
                query = None

            try:
                dashboard_name = form_data["dashboard"]
                name = form_data["title"]
                recipe_id = request.POST.get("recipe_id")
                settings = {"columns": request.POST.getlist("columns"), "size": form_data["size"]}

                self.dashboard_data, created = get_or_create_dashboard_data(
                    dashboard_name, self.organization, name, recipe_id, query_from, query, template, settings
                )
                if created:
                    messages.success(request, "Dashboard item has been created.")
                else:
                    messages.warning(
                        request,
                        "The dashboard item that you were trying to add already exists on the selected dashboard."
                        "If it was hidden on the dashboard, it is now visible.",
                    )

                query_params = urlencode({"dashboard": dashboard_name})
                return redirect(
                    reverse("organization_crisis_room", kwargs={"organization_code": self.organization.code})
                    + "?"
                    + query_params
                )
            except IntegrityError:
                messages.error(
                    request,
                    "Dashboard item could not be created, because this dashboard has reached the maximum of 16 items.",
                )

            return redirect(reverse("ooi_list", kwargs={"organization_code": self.organization.code}))
        else:
            return self.form_invalid(form)
