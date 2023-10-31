import logging
from dataclasses import dataclass
from typing import Dict, List

from account.models import KATUser
from django.conf import settings
from django.contrib import messages
from django.urls.base import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from tools.forms.base import ObservedAtForm
from tools.models import Organization
from tools.view_helpers import BreadcrumbsMixin

from octopoes.connector import ConnectorException
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models.ooi.findings import RiskLevelSeverity
from rocky.views.mixins import ObservedAtMixin
from rocky.views.ooi_view import ConnectorFormMixin

logger = logging.getLogger(__name__)


# dataclass to store finding type counts
@dataclass
class OrganizationFindingCountPerSeverity:
    name: str
    code: str
    finding_count_per_severity: Dict[str, int]

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
    breadcrumbs = [
        {"url": "", "text": "Crisis Room"},
    ]

    def sort_by_total(
        self, finding_counts: List[OrganizationFindingCountPerSeverity]
    ) -> List[OrganizationFindingCountPerSeverity]:
        is_desc = self.request.GET.get("sort_total_by", "desc") != "asc"
        return sorted(finding_counts, key=lambda x: x.total, reverse=is_desc)

    def sort_by_severity(
        self, finding_counts: List[OrganizationFindingCountPerSeverity]
    ) -> List[OrganizationFindingCountPerSeverity]:
        is_desc = self.request.GET.get("sort_critical_by", "desc") != "asc"
        return sorted(finding_counts, key=lambda x: x.total_critical, reverse=is_desc)

    def get_finding_type_severity_count(self, organization: Organization) -> Dict[str, int]:
        try:
            api_connector = OctopoesAPIConnector(settings.OCTOPOES_API, organization.code)
            return api_connector.count_findings_by_severity(valid_time=self.get_observed_at())
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
                name=org.name,
                code=org.code,
                finding_count_per_severity=self.get_finding_type_severity_count(org),
            )
            for org in user.organizations
        ]

        context["breadcrumb_list"] = [
            {"url": reverse("crisis_room"), "text": "CRISIS ROOM"},
        ]

        context["organizations"] = user.organizations

        context["org_finding_counts_per_severity"] = self.sort_by_total(org_finding_counts_per_severity)
        context["org_finding_counts_per_severity_critical"] = self.sort_by_severity(org_finding_counts_per_severity)

        context["observed_at_form"] = self.get_connector_form()
        context["observed_at"] = self.get_observed_at().date()

        return context
