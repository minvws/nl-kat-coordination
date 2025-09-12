import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import structlog
from django.conf import settings
from django.http.request import HttpRequest
from django.urls import reverse
from django.views.generic import TemplateView
from httpx import HTTPStatusError

from crisis_room.management.commands.dashboards import FINDINGS_DASHBOARD_NAME
from crisis_room.models import DashboardData
from files.models import File
from octopoes.models.exception import ObjectNotFoundException
from octopoes.models.ooi.reports import HydratedReport
from openkat.models import Organization, OrganizationMember
from reports.report_types.findings_report.report import SEVERITY_OPTIONS

logger = structlog.get_logger(__name__)


class DashboardService:
    @staticmethod
    def get_organizations_findings(report_data: dict[str, Any]) -> dict[str, Any]:
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

    def get_reports(self, valid_time: datetime, dashboards_data) -> dict[UUID, HydratedReport]:
        """
        Returns for each recipe ID query'ed, the latest (valid_time) HydratedReport.
        """
        report_filters = [(data.dashboard.organization.code, str(data.recipe)) for data in dashboards_data]

        if report_filters:
            org_code, _ = report_filters[0]
            # We need at least 1 org connector to fetch reports from all other orgs.
            connector = settings.OCTOPOES_FACTORY(org_code)
            try:
                return connector.bulk_list_reports(valid_time, report_filters)
            except (HTTPStatusError, ObjectNotFoundException):
                return {}
        return {}

    def collect_findings_dashboard(self, organizations: list[Organization]) -> list[dict[str, Any]]:
        findings_dashboard = []

        dashboards_data = DashboardData.objects.filter(
            dashboard__name=FINDINGS_DASHBOARD_NAME, dashboard__organization__in=organizations, findings_dashboard=True
        )

        reports: dict[UUID, HydratedReport] = self.get_reports(datetime.now(timezone.utc), dashboards_data)

        raw_ids = [hydrated_report.data_raw_id for _, hydrated_report in reports.items() if hydrated_report]
        report_data_from_bytes = {
            str(raw.id): json.loads(raw.file.read()) for raw in File.objects.filter(id__in=raw_ids)
        }

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
        context["breadcrumbs"] = [{"url": reverse("crisis_room"), "text": "Crisis room"}]
        context["organizations_dashboards"] = self.organizations_findings
        context["organizations_findings_summary"] = self.organizations_findings_summary
        return context
