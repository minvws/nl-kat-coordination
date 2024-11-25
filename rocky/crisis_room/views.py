from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

import structlog
from account.models import KATUser
from django.conf import settings
from django.contrib import messages
from django.urls.base import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from reports.report_types.concatenated_report.report import ConcatenatedReport
from reports.report_types.findings_report.report import FindingsReport
from reports.report_types.helpers import get_ooi_types_with_report
from tools.forms.base import ObservedAtForm
from tools.models import Organization, OrganizationMember
from tools.ooi_helpers import create_ooi
from tools.view_helpers import BreadcrumbsMixin

from octopoes.connector import ConnectorException
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import ScanLevel, ScanProfileType
from octopoes.models.ooi.findings import RiskLevelSeverity
from octopoes.models.ooi.reports import ReportRecipe
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
    default_scan_level = {ScanLevel.L2}
    default_scan_profiles = {ScanProfileType.EMPTY, ScanProfileType.INHERITED, ScanProfileType.DECLARED}
    default_valid_time = datetime.now(timezone.utc)

    def get_user_organizations(self):
        return [member.organization for member in OrganizationMember.objects.filter(user=self.request.user)]

    def get_query(self):
        return {
            "query": {
                "ooi_types": [ooi_type.__name__ for ooi_type in get_ooi_types_with_report()],
                "scan_level": self.default_scan_level,
                "scan_type": self.default_scan_profiles,
                "search_string": "",
                "order_by": "object_type",
                "asc_desc": "desc",
            }
        }

    def create_report_recipe_for_all_organizations(self):
        report_recipe = ReportRecipe(
            recipe_id=uuid4(),
            report_name_format="Findings Report for ${oois_count} objects",
            subreport_name_format="Findings Report for ${ooi}",
            input_recipe=self.get_query(),
            parent_report_type=ConcatenatedReport.id,
            report_types=[FindingsReport.id],
            cron_expression="0 0 * * *",
        )

        organizations = self.get_user_organizations()

        for organization in organizations:
            octopoes_client = OctopoesAPIConnector(
                settings.OCTOPOES_API, organization.code, timeout=settings.ROCKY_OUTGOING_REQUEST_TIMEOUT
            )

            bytes_client = get_bytes_client(organization.code)

            create_ooi(
                api_connector=octopoes_client,
                bytes_client=bytes_client,
                ooi=report_recipe,
                observed_at=self.default_valid_time,
            )

        return report_recipe

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["recipe"] = self.create_report_recipe_for_all_organizations()

        return context
