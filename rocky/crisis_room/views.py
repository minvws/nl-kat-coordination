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
from django.http import HttpResponse
from django.http.request import HttpRequest
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView
from httpx import HTTPStatusError
from reports.report_types.findings_report.report import SEVERITY_OPTIONS
from tools.forms.ooi_form import _EXCLUDED_OOI_TYPES
from tools.models import Organization, OrganizationMember

from crisis_room.forms import AddDashboardForm
from crisis_room.management.commands.dashboards import (
    FINDINGS_DASHBOARD_NAME,
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

    def get_reports(self, valid_time: datetime, dashboards_data) -> dict[DashboardData, HydratedReport]:
        """
        Returns for each recipe ID query'ed, the latest (valid_time) HydratedReport.
        """

        dashboard_items = {}
        reports = {}
        report_filters = []

        for dashboard_data in dashboards_data:
            if dashboard_data.recipe:
                # collect them to prepare for 1 octopoes call to later rejoin dashboard data by recipe id
                report_filters.append((dashboard_data.dashboard.organization.code, str(dashboard_data.recipe)))
                dashboard_items[dashboard_data] = dashboard_data.recipe

        if report_filters:
            org_code, _ = report_filters[0]
            # We need at least 1 org connector to fetch reports from all other orgs.
            connector = OctopoesAPIConnector(
                settings.OCTOPOES_API, org_code, timeout=settings.ROCKY_OUTGOING_REQUEST_TIMEOUT
            )
            try:
                reports_per_recipe: dict[UUID, HydratedReport] = connector.bulk_list_reports(valid_time, report_filters)

                for dashboard_data, recipe_id in dashboard_items.items():
                    try:
                        reports[dashboard_data] = reports_per_recipe[recipe_id]
                    except KeyError:
                        continue
                return reports
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

    def collect_findings_dashboard(self, organizations: list[Organization]) -> list[dict[str, Any]]:
        findings_dashboard = []

        dashboards_data = DashboardData.objects.filter(
            dashboard__name=FINDINGS_DASHBOARD_NAME, dashboard__organization__in=organizations, findings_dashboard=True
        )

        reports: dict[DashboardData, HydratedReport] = self.get_reports(datetime.now(timezone.utc), dashboards_data)

        raw_ids = [hydrated_report.data_raw_id for _, hydrated_report in reports.items() if hydrated_report]
        report_data_from_bytes = self.get_report_bytes_data(raw_ids)

        for _, hydrated_report in reports.items():
            try:
                hydrated_report_data = report_data_from_bytes[hydrated_report.data_raw_id]
                report_data = self.get_organizations_findings(hydrated_report_data)
                findings_dashboard.append({"report": hydrated_report, "report_data": report_data})
            except KeyError:
                continue

        return findings_dashboard

    @staticmethod
    def get_organizations_findings_summary(organizations_findings: list[dict[str, Any]]) -> dict[str, Any]:
        summary: dict[str, Any] = {
            "total_by_severity_per_finding_type": {severity: 0 for severity in SEVERITY_OPTIONS},
            "total_by_severity": {severity: 0 for severity in SEVERITY_OPTIONS},
            "total_finding_types": 0,
            "total_occurrences": 0,
        }

        summary_added = False

        for data in organizations_findings:
            if "findings" in data["report_data"] and "summary" in data["report_data"]["findings"]:
                for summary_item, data in data["report_data"]["findings"]["summary"].items():
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

    def get_dashboard(self, dashboard_name, organization):
        return Dashboard.objects.get(organization=organization, name=dashboard_name)

    def get_ooi_list(self, dashboard_data):
        query = json.loads(dashboard_data.query)
        list_limit = 20
        ooi_list = []

        if dashboard_data.query_from == "object_list":
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
                limit=list_limit,
                scan_level=scan_level,
                scan_profile_type=scan_profile_type,
                search_string=query["search_string"],
                order_by=query["order_by"],
                asc_desc=query["asc_desc"],
            ).items

        return ooi_list

    def get_dashboard_data(self, dashboard_name, organization):
        dashboard_items = {}
        data = {}

        report_dashboards = []
        dashboards_data = DashboardData.objects.filter(
            dashboard__name=dashboard_name, dashboard__organization=organization, display_in_dashboard=True
        )

        for dashboard_data in dashboards_data:
            if not dashboard_data.recipe:
                data = {"ooi_list": self.get_ooi_list(dashboard_data), "query": dashboard_data.query}
                dashboard_items[dashboard_data] = data
            else:
                report_dashboards.append(dashboard_data)

        if report_dashboards:
            self.get_reports(datetime.now(timezone.utc), report_dashboards)

        return dashboard_items


class CrisisRoomView(TemplateView):
    """This is the Crisis Room for all organizations."""

    template_name = "crisis_room.html"

    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs)

        dashboard_service = DashboardService()
        organizations = self.get_user_organizations()

        self.organizations_findings = dashboard_service.collect_findings_dashboard(organizations)
        self.organizations_findings_summary = dashboard_service.get_organizations_findings_summary(
            self.organizations_findings
        )

    def get_user_organizations(self) -> list[Organization]:
        return [member.organization for member in OrganizationMember.objects.filter(user=self.request.user)]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"url": reverse("crisis_room"), "text": "Crisis Room"}]
        context["organizations_dashboards"] = self.organizations_findings
        context["organizations_findings_summary"] = self.organizations_findings_summary
        return context


class OrganizationsCrisisRoomView(TemplateView, OrganizationView):
    """This is the Crisis Room for a single organization."""

    template_name = "organization_crisis_room.html"
    dashboard_service = DashboardService()

    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs)

        # Default is the findings dashboard
        self.dashboard_name = self.request.GET.get("dashboard", FINDINGS_DASHBOARD_NAME)

        # Create the dashboard tabs
        self.get_dashboard_navigation = self.dashboard_service.get_dashboard_navigation(self.organization)

        self.get_dashboard = self.dashboard_service.get_dashboard(self.dashboard_name, self.organization)
        self.get_dashboard_data = self.dashboard_service.get_dashboard_data(self.dashboard_name, self.organization)

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Create a new dashboard tab."""
        dashboard_name = request.POST.get("dashboard_name")
        query_params = ""
        try:
            dashboard, created = get_or_create_dashboard(dashboard_name, self.organization)
            if created:
                query_params = "?" + urlencode({"dashboard": dashboard.name})
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["all_dashboard_names"] = self.get_dashboard_navigation
        context["dashboard_data"] = self.get_dashboard_data
        context["dashboard"] = self.get_dashboard
        context["organization"] = self.organization
        context["add_dashboard_form"] = AddDashboardForm
        context["breadcrumbs"] = [
            {
                "url": reverse("organization_crisis_room", kwargs={"organization_code": self.organization.code}),
                "text": "Crisis Room",
            }
        ]
        return context


class AddDashboardItemView(OrganizationView, TemplateView):
    """This is the Crisis Room for a single organization."""

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Add dashboard item and redirect to the selected dashboard."""

        dashboard_name = request.POST.get("dashboard")
        recipe_id = request.POST.get("recipe_id")
        query_from = request.POST.get("query_from")
        query = None
        template = request.POST.get("template")

        # Settings:
        title = request.POST.get("title")
        sort_by = request.POST.get("sort_by").split("-")
        order_by = sort_by[0]
        asc_desc = sort_by[1]
        limit = request.POST.get("limit")
        columns = request.POST.get("columns")
        size = request.POST.get("size")

        logger.error(
            "Show settings as test: title=%s, sort_by=%s, limit=%s, columns=%s, size=%s",
            title,
            sort_by,
            limit,
            columns,
            size,
        )

        if query_from == "object_list":
            template = "partials/dashboard_ooi_list.html"
            query = {
                "ooi_types": request.POST.getlist("ooi_type"),
                "scan_level": request.POST.getlist("clearance_level"),
                "scan_profile_type": request.POST.getlist("clearance_type"),
                "search_string": request.POST.get("search_string"),
                "order_by": order_by,
                "asc_desc": asc_desc,
                "limit": limit,
            }

        try:
            self.dashboard_data, created = get_or_create_dashboard_data(
                dashboard_name, self.organization, recipe_id, query_from, query, template
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
