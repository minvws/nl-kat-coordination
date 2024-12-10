from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import structlog
from account.models import KATUser
from django.conf import settings
from django.contrib import messages
from django.db.models.query import QuerySet
from django.http.request import HttpRequest
from django.urls.base import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from pydantic import TypeAdapter
from reports.report_types.findings_report.report import SEVERITY_OPTIONS
from tools.forms.base import ObservedAtForm
from tools.models import Organization, OrganizationMember
from tools.view_helpers import BreadcrumbsMixin

from crisis_room.models import DashboardData
from octopoes.connector import ConnectorException
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import Reference
from octopoes.models.ooi.findings import RiskLevelSeverity
from rocky.bytes_client import get_bytes_client
from rocky.views.mixins import ObservedAtMixin
from rocky.views.ooi_view import ConnectorFormMixin

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
    template_name = "crisis_room/crisis_room.html"

    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs)
        self.dashboards_data = self.get_dashboards_data()
        self.findings_report_data = self.get_findings_report_data()
        self.findings_report_summary = self.get_findings_report_summary()

    def get_user_organizations(self) -> list[Organization]:
        return [member.organization for member in OrganizationMember.objects.filter(user=self.request.user)]

    def get_octopoes_client(self, organization: Organization) -> OctopoesAPIConnector:
        return OctopoesAPIConnector(
            settings.OCTOPOES_API, organization.code, timeout=settings.ROCKY_OUTGOING_REQUEST_TIMEOUT
        )

    def get_dashboards_data(self) -> QuerySet[DashboardData]:
        organizations = self.get_user_organizations()
        dashboards_data = DashboardData.objects.filter(dashboard__organization__in=[org.pk for org in organizations])
        return dashboards_data

    def get_report_data(self, dashboard_data: DashboardData) -> dict[str, Any]:
        valid_time = datetime.now(timezone.utc)
        octopoes_client = self.get_octopoes_client(dashboard_data.dashboard.organization)

        reports = octopoes_client.query(
            "ReportRecipe.<report_recipe[is Report]",
            valid_time=valid_time,
            source=Reference.from_str(dashboard_data.recipe),
        )
        if reports:
            reports.sort(key=lambda ooi: ooi.date_generated, reverse=True)
            report = reports[0]

            bytes_client = get_bytes_client(dashboard_data.dashboard.organization.code)
            bytes_client.login()

            return TypeAdapter(Any, config={"arbitrary_types_allowed": True}).validate_json(
                bytes_client.get_raw(raw_id=report.data_raw_id)
            )
        return {}

    def get_findings_report_data(self) -> dict[Organization, dict[str, Any]]:
        reports = {}
        dashboards_data = self.get_dashboards_data()
        # TODO: filter dashboard data, so we only have the dashboard of Findings with ReportRecipe that contains:
        # 1. Name == Crisis Room Aggregate Report
        # 2. Parent-report-type == "aggregate-organization-report"
        # 3. Report-types contains "system-report" and "findings-report"

        for dashboard_data in dashboards_data:
            if dashboard_data.dashboard.organization not in reports:
                reports[dashboard_data.dashboard.organization] = self.get_report_data(dashboard_data)

        return reports

    def get_findings_report_summary(self):
        dashboards_data = self.get_dashboards_data()
        summary: dict[str, Any] = {
            "total_by_severity": {severity: 0 for severity in SEVERITY_OPTIONS},
            "total_by_severity_per_finding_type": {severity: 0 for severity in SEVERITY_OPTIONS},
            "total_finding_types": 0,
            "total_occurrences": 0,
        }

        for dashboard_data in dashboards_data:
            report_data = self.get_report_data(dashboard_data)
            if "findings" in report_data:
                for summary_item, data in report_data["findings"]["summary"].items():
                    if isinstance(data, dict):
                        for severity, total in data.items():
                            summary[summary_item][severity] += total
                    else:
                        summary[summary_item] += data

        return summary

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["dashboards_data"] = self.dashboards_data
        context["findings_report_data"] = self.findings_report_data
        context["findings_report_summary"] = self.findings_report_summary
        return context
