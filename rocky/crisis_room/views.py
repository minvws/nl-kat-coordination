from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import structlog
from django.conf import settings
from django.http.request import HttpRequest
from django.urls import reverse
from django.views.generic import TemplateView
from httpx import HTTPStatusError
from pydantic import TypeAdapter
from reports.report_types.findings_report.report import SEVERITY_OPTIONS
from tools.models import Organization, OrganizationMember

from crisis_room.management.commands.dashboards import FINDINGS_DASHBOARD_NAME
from crisis_room.models import DashboardData
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models.exception import ObjectNotFoundException
from octopoes.models.ooi.reports import HydratedReport
from rocky.bytes_client import BytesClient, get_bytes_client

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


class CrisisRoom(TemplateView):
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
