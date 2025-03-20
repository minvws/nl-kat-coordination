from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode
from uuid import UUID

import structlog
from account.mixins import OrganizationView
from django.conf import settings
from django.http import HttpResponse
from django.http.request import HttpRequest
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView
from httpx import HTTPStatusError
from pydantic import TypeAdapter
from reports.report_types.findings_report.report import SEVERITY_OPTIONS
from tools.models import Organization, OrganizationMember

from crisis_room.management.commands.dashboards import FINDINGS_DASHBOARD_NAME, get_or_create_dashboard_data
from crisis_room.models import DashboardData
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models.exception import ObjectNotFoundException
from octopoes.models.ooi.reports import HydratedReport
from rocky.bytes_client import BytesClient, get_bytes_client
from rocky.views.mixins import OOIList

logger = structlog.get_logger(__name__)


class DashboardService:
    observed_at = datetime.now(timezone.utc)  # we can later set any observed_at

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

    @staticmethod
    def get_octopoes_client(organization_code: str) -> OctopoesAPIConnector:
        return OctopoesAPIConnector(
            settings.OCTOPOES_API, organization_code, timeout=settings.ROCKY_OUTGOING_REQUEST_TIMEOUT
        )

    @staticmethod
    def get_reports(
        observed_at: datetime, octopoes_api_connector: OctopoesAPIConnector, recipe_id: str
    ) -> list[HydratedReport]:
        try:
            return octopoes_api_connector.list_reports(valid_time=observed_at, recipe_id=UUID(recipe_id)).items
        except (HTTPStatusError, ObjectNotFoundException):
            return []

    @staticmethod
    def get_report_bytes_data(bytes_client: BytesClient, data_raw_id: str):
        bytes_client.login()
        return TypeAdapter(Any, config={"arbitrary_types_allowed": True}).validate_json(
            bytes_client.get_raw(raw_id=data_raw_id)
        )

    def collect_findings_dashboard(
        self, organizations: list[Organization]
    ) -> dict[Organization, dict[DashboardData, dict[str, Any]]]:
        findings_dashboard = {}

        dashboards_data = DashboardData.objects.filter(
            dashboard__name=FINDINGS_DASHBOARD_NAME, dashboard__organization__in=organizations, findings_dashboard=True
        )

        for data in dashboards_data:
            organization = data.dashboard.organization
            octopoes_client = self.get_octopoes_client(organization.code)
            bytes_client = get_bytes_client(organization.code)
            recipe_id = data.recipe

            # get reports with recipe id
            # TODO: change this method to get_report, since there's only one report that belongs to a recipe_id
            reports = self.get_reports(self.observed_at, octopoes_client, recipe_id)

            if reports:
                report = reports[0]
                report_data_from_bytes = self.get_report_bytes_data(bytes_client, report.data_raw_id)
                report_data = self.get_organizations_findings(report_data_from_bytes)

                if report_data:
                    findings_dashboard[organization] = {data: {"report": report, "report_data": report_data}}
            else:
                findings_dashboard[organization] = {}

        return findings_dashboard

    @staticmethod
    def get_organizations_findings_summary(
        organizations_findings: dict[Organization, dict[DashboardData, dict[str, Any]]],
    ) -> dict[str, Any]:
        summary: dict[str, Any] = {
            "total_by_severity_per_finding_type": {severity: 0 for severity in SEVERITY_OPTIONS},
            "total_by_severity": {severity: 0 for severity in SEVERITY_OPTIONS},
            "total_finding_types": 0,
            "total_occurrences": 0,
        }

        summary_added = False

        for organization, organizations_data in organizations_findings.items():
            for data in organizations_data.values():
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

    def get_all_dashboard_names(self, organization):
        dashboard_names = []
        dashboards_data = DashboardData.objects.filter(dashboard__organization=organization, display_in_dashboard=True)
        for data in dashboards_data:
            dashboard_names.append(data.dashboard.name)
        return list(set(dashboard_names))

    def get_dashboard_data(self, dashboard_name, organization):
        dashboard = {}

        dashboard_datas = DashboardData.objects.filter(
            dashboard__name=dashboard_name, dashboard__organization=organization, display_in_dashboard=True
        )

        for data in dashboard_datas:
            octopoes_client = self.get_octopoes_client(organization.code)
            bytes_client = get_bytes_client(organization.code)

            recipe_id = data.recipe
            query_from = data.query_from

            if recipe_id:
                reports = self.get_reports(self.observed_at, octopoes_client, recipe_id)

                if reports:
                    report = reports[0]
                    report_data_from_bytes = self.get_report_bytes_data(bytes_client, report.data_raw_id)
                    report_data = self.get_organizations_findings(report_data_from_bytes)
                    if report.name == FINDINGS_DASHBOARD_NAME or report_data:
                        dashboard[data] = {"report": report, "report_data": report_data}
            elif query_from == "object_list":
                ooi_list = OOIList(**data.query)
                dashboard[data] = {"ooi_data": ooi_list}

        return dashboard


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
        context["breadcrumbs"] = [{"url": reverse("crisis_room"), "text": "Crisis "}]
        context["organizations_dashboards"] = self.organizations_findings
        context["organizations_findings_summary"] = self.organizations_findings_summary
        return context


class OrganizationsCrisisRoomView(OrganizationView, TemplateView):
    """This is the Crisis Room for a single organization."""

    template_name = "organization_crisis_room.html"

    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs)

        dashboard_service = DashboardService()
        dashboard_name = self.request.GET.get("dashboard")
        self.organization = OrganizationMember.objects.filter(user=self.request.user)[0].organization
        self.get_dashboard_data = dashboard_service.get_dashboard_data(dashboard_name, self.organization)
        self.get_all_dashboard_names = dashboard_service.get_all_dashboard_names(self.organization)

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Go to the selected dashboard or, in case that no dashboard has been selected, go to the first tab."""
        self.query_params = urlencode({"dashboard": self.get_all_dashboard_names[0]})

        if not self.get_dashboard_data:
            return redirect(
                reverse("organization_crisis_room", kwargs={"organization_code": self.organization.code})
                + "?"
                + self.query_params
            )
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["all_dashboard_names"] = self.get_all_dashboard_names
        context["dashboard"] = self.get_dashboard_data
        return context


class AddDashboardItemView(OrganizationView, TemplateView):
    """This is the Crisis Room for a single organization."""

    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs)

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Go to the selected dashboard or, in case that no dashboard has been selected, go to the first tab."""
        if self.dashboard_data:
            query_params = urlencode({"dashboard": self.dashboard_data.dashboard.name})
            return redirect(
                reverse("organization_crisis_room", kwargs={"organization_code": self.organization.code})
                + "?"
                + query_params
            )

        return redirect(reverse("organization_crisis_room", kwargs={"organization_code": self.organization.code}))

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Add dashboard item and return to the selected dashboard."""
        # TODO: fix query
        query = {
            "valid_time": self.observed_at,
            "ooi_types": self.filtered_ooi_types,
            "scan_level": self.clearance_levels,
            "scan_profile_type": self.clearance_types,
            "search_string": self.search_string,
            "order_by": self.order_by,
            "asc_desc": self.sorting_order,
        }
        # TODO: replace dashboard_name to 'self.request.GET.get("dashboard")'
        dashboard_name = "Test Dashboard"
        recipe_id = self.request.GET.get("recipe_id")
        query_from = self.request.GET.get("query_from")
        template = self.request.GET.get("template")

        if query_from == "object_list":
            template = "oois/ooi_list.html"

        self.dashboard_data = get_or_create_dashboard_data(
            dashboard_name, self.organization, recipe_id, query_from, query, template
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
