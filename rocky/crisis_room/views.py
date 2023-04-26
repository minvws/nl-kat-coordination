import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Set

from account.models import KATUser
from django.conf import settings
from django.contrib import messages
from django.urls.base import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from django_otp.decorators import otp_required
from tools.forms.base import ObservedAtForm
from tools.models import OOIInformation, Organization
from tools.ooi_helpers import (
    RiskLevelSeverity,
    get_risk_level_score,
    get_risk_level_score_for_cve,
    get_risk_level_score_for_retirejs,
    get_risk_level_score_for_snyk,
)
from tools.view_helpers import BreadcrumbsMixin, convert_date_to_datetime
from two_factor.views.utils import class_view_decorator

from octopoes.connector import ConnectorException
from octopoes.connector.octopoes import OctopoesAPIConnector
from rocky.views.ooi_view import ConnectorFormMixin

logger = logging.getLogger(__name__)


# dataclass to store finding type counts
@dataclass
class OrganizationFindingTypeCount:
    name: str
    code: str
    finding_count_per_severity: Dict[str, int]

    @property
    def total(self) -> int:
        return sum(self.finding_count_per_severity.values())

    @property
    def total_critical(self) -> int:
        return self.finding_count_per_severity[RiskLevelSeverity.CRITICAL.value]


def load_finding_type_risks(finding_types: Set[str]) -> Dict[str, str]:
    """Load finding type from db and map to uniform dataclass"""

    # initialize default entry for each finding_type
    severities = {ft: RiskLevelSeverity.CRITICAL.value for ft in finding_types}

    # query for data in ooi information table and override for each hit
    information_records = list(OOIInformation.objects.filter(id__in=finding_types))
    for ooi_info in information_records:
        finding_type_type = ooi_info.pk.split("|")[0]
        # hook into the old code to re-use the risk level calculation logic
        # FIXME: refactor this duplicated logic in future PR
        if finding_type_type == "CVEFindingType":
            risk_level = get_risk_level_score_for_cve(ooi_info.data)
        elif finding_type_type == "RetireJSFindingType":
            risk_level = get_risk_level_score_for_retirejs(ooi_info.data)
        elif finding_type_type == "SnykFindingType":
            risk_level = get_risk_level_score_for_snyk(ooi_info.data)
        else:
            risk_level = get_risk_level_score(ooi_info.data)

        severities[ooi_info.pk] = risk_level["risk_level_severity"]

    return severities


class CrisisRoomBreadcrumbsMixin(BreadcrumbsMixin):
    breadcrumbs = [
        {"url": "", "text": "Crisis Room"},
    ]


@class_view_decorator(otp_required)
class CrisisRoomView(CrisisRoomBreadcrumbsMixin, ConnectorFormMixin, TemplateView):
    template_name = "crisis_room/crisis_room.html"
    connector_form_class = ObservedAtForm

    def sort_finding_list_by_total(
        self, org_finding_type_counts: List[OrganizationFindingTypeCount]
    ) -> List[OrganizationFindingTypeCount]:
        is_desc = self.request.GET.get("sort_total_by", "desc") != "asc"
        return sorted(org_finding_type_counts, key=lambda x: x.total, reverse=is_desc)

    def sort_finding_list_by_critical(
        self, org_finding_type_counts: List[OrganizationFindingTypeCount]
    ) -> List[OrganizationFindingTypeCount]:
        is_desc = self.request.GET.get("sort_critical_by", "desc") != "asc"
        return sorted(org_finding_type_counts, key=lambda x: x.total_critical, reverse=is_desc)

    def get_finding_type_count(self, organization: Organization) -> Dict[str, int]:
        try:
            api_connector = OctopoesAPIConnector(settings.OCTOPOES_API, organization.code)
            return api_connector.get_finding_type_count(valid_time=self.get_observed_at())
        except ConnectorException:
            messages.add_message(
                self.request, messages.ERROR, _("Failed to get list of findings, check server logs for more details.")
            )
            logger.exception("Failed to get list of findings for organization %s", organization.code)
            return {}

    def get_observed_at(self) -> datetime:
        if "observed_at" not in self.request.GET:
            return datetime.now(timezone.utc)

        try:
            datetime_format = "%Y-%m-%d"
            return convert_date_to_datetime(datetime.strptime(self.request.GET.get("observed_at"), datetime_format))
        except ValueError:
            return datetime.now(timezone.utc)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user: KATUser = self.request.user

        # query each organization's finding type count
        finding_type_counts = {}
        for org in user.organizations:
            finding_type_counts[(org.code, org.name)] = self.get_finding_type_count(org)

        # find all unique finding types and query their severity
        unique_finding_types = set()
        for org_code, finding_type_count in finding_type_counts.items():
            unique_finding_types.update(finding_type_count.keys())

        severities = load_finding_type_risks(unique_finding_types)

        # aggregate per organization, per severity
        org_finding_type_counts = []
        for (org_code, org_name), finding_type_count in finding_type_counts.items():
            org_severity_count: Dict[str, int] = {severity_level.value: 0 for severity_level in RiskLevelSeverity}
            for finding_type, count in finding_type_count.items():
                finding_type_severity = severities[finding_type]
                org_severity_count[finding_type_severity] += count
            org_finding_type_counts.append(OrganizationFindingTypeCount(org_name, org_code, org_severity_count))

        context["breadcrumb_list"] = [
            {"url": reverse("crisis_room"), "text": "CRISIS ROOM"},
        ]

        context["organizations"] = user.organizations

        context["org_finding_type_counts"] = self.sort_finding_list_by_total(org_finding_type_counts)
        context["org_finding_type_counts_critical"] = self.sort_finding_list_by_critical(org_finding_type_counts)

        context["observed_at_form"] = self.get_connector_form()
        context["observed_at"] = self.get_observed_at().date()

        return context
