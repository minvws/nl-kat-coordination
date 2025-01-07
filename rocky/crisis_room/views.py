from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import structlog
from account.models import KATUser
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse
from django.http.request import HttpRequest
from django.shortcuts import redirect
from django.urls.base import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from pydantic import TypeAdapter
from reports.report_types.findings_report.report import SEVERITY_OPTIONS
from tools.forms.base import ObservedAtForm
from tools.models import Organization, OrganizationMember
from tools.view_helpers import BreadcrumbsMixin

from crisis_room.management.commands.dashboard import FINDINGS_DASHBOARD_NAME
from crisis_room.models import DashboardData
from octopoes.connector import ConnectorException
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import Reference
from octopoes.models.ooi.findings import RiskLevelSeverity
from rocky.bytes_client import BytesClient, get_bytes_client
from rocky.views.mixins import ConnectorFormMixin, ObservedAtMixin

logger = structlog.get_logger(__name__)


# dataclass to store finding type counts
@dataclass
class OrganizationFindingCountPerSeverity:
    name: str
    code: str
    finding_count_per_severity: dict[str, int]

    @property
    def total(self) -> int:
        return sum(self.finding_count_per_severity.values())

    @property
    def total_critical(self) -> int:
        try:
            return self.finding_count_per_severity[RiskLevelSeverity.CRITICAL.value]
        except KeyError:
            return 0


class CrisisRoomView(BreadcrumbsMixin, ConnectorFormMixin, ObservedAtMixin, TemplateView):
    template_name = "crisis_room/crisis_room.html"
    connector_form_class = ObservedAtForm
    breadcrumbs = [{"url": "", "text": "Crisis Room"}]

    def sort_by_total(
        self, finding_counts: list[OrganizationFindingCountPerSeverity]
    ) -> list[OrganizationFindingCountPerSeverity]:
        is_desc = self.request.GET.get("sort_total_by", "desc") != "asc"
        return sorted(finding_counts, key=lambda x: x.total, reverse=is_desc)

    def sort_by_severity(
        self, finding_counts: list[OrganizationFindingCountPerSeverity]
    ) -> list[OrganizationFindingCountPerSeverity]:
        is_desc = self.request.GET.get("sort_critical_by", "desc") != "asc"
        return sorted(finding_counts, key=lambda x: x.total_critical, reverse=is_desc)

    def get_finding_type_severity_count(self, organization: Organization) -> dict[str, int]:
        try:
            api_connector = OctopoesAPIConnector(
                settings.OCTOPOES_API, organization.code, timeout=settings.ROCKY_OUTGOING_REQUEST_TIMEOUT
            )
            return api_connector.count_findings_by_severity(valid_time=self.observed_at)
        except ConnectorException:
            messages.add_message(
                self.request,
                messages.ERROR,
                _("Failed to get list of findings for organization {}, check server logs for more details.").format(
                    organization.code
                ),
            )
            logger.exception("Failed to get list of findings for organization %s", organization.code)
            return {}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user: KATUser = self.request.user

        # query each organization's finding type count
        org_finding_counts_per_severity = [
            OrganizationFindingCountPerSeverity(
                name=org.name, code=org.code, finding_count_per_severity=self.get_finding_type_severity_count(org)
            )
            for org in user.organizations
        ]

        context["breadcrumb_list"] = [{"url": reverse("crisis_room"), "text": "CRISIS ROOM"}]
        context["organizations"] = user.organizations

        context["org_finding_counts_per_severity"] = self.sort_by_total(org_finding_counts_per_severity)
        context["org_finding_counts_per_severity_critical"] = self.sort_by_severity(org_finding_counts_per_severity)

        context["observed_at_form"] = self.get_connector_form()
        context["observed_at"] = self.observed_at.date()

        return context


class CrisisRoomAllOrganizations(TemplateView):
    """
    Crisis Room langding page.
    """

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return redirect(reverse("crisis_room_findings"))


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
    def get_reports(valid_time: datetime, octopoes_client: OctopoesAPIConnector, recipe_id: str):
        return octopoes_client.query(
            "ReportRecipe.<report_recipe[is Report]", valid_time=valid_time, source=Reference.from_str(recipe_id)
        )

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
            reports = self.get_reports(self.observed_at, octopoes_client, recipe_id)

            if reports:
                reports.sort(key=lambda ooi: ooi.date_generated, reverse=True)
                report = reports[0]
                report_data_from_bytes = self.get_report_bytes_data(bytes_client, report.data_raw_id)
                report_data = self.get_organizations_findings(report_data_from_bytes)

                if report_data:
                    findings_dashboard[organization] = {data: {"report": report, "report_data": report_data}}

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


class CrisisRoomFindings(TemplateView):
    template_name = "crisis_room_findings.html"

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
        context["organizations_dashboards"] = self.organizations_findings
        context["organizations_findings_summary"] = self.organizations_findings_summary
        return context
