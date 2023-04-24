import logging
from typing import Any, Dict, List, Optional

from account.mixins import OrganizationView
from django.contrib import messages
from django.urls.base import reverse_lazy
from django.utils.translation import gettext_lazy as _
from tools.ooi_helpers import RiskLevelSeverity, get_finding_type_from_finding, get_knowledge_base_data_for_ooi
from tools.view_helpers import BreadcrumbsMixin

from octopoes.connector import ConnectorException
from octopoes.models import DEFAULT_SCAN_LEVEL_FILTER, DEFAULT_SCAN_PROFILE_TYPE_FILTER
from octopoes.models.ooi.findings import Finding, MutedFinding
from rocky.views.mixins import OOIList
from rocky.views.ooi_view import BaseOOIListView

logger = logging.getLogger(__name__)


def sort_by_severity_desc(findings) -> List[Dict[str, Any]]:
    # Sorting is stable (when multiple records have the same key, their original
    # order is preserved) so if we first sort by finding id the findings with
    # the same risk score will be sorted by finding id
    sorted_by_finding_id = sorted(findings, key=lambda x: x["finding_type"].id)
    sorted_findings = sorted(sorted_by_finding_id, key=lambda x: x["risk_level_score"], reverse=True)
    for index, finding in enumerate(sorted_findings, start=1):
        finding["finding_number"] = index
    return sorted_findings


def generate_findings_metadata(
    findings: OOIList,
    muted_findings: OOIList,
    severity_filter: Optional[List[RiskLevelSeverity]] = None,
) -> List[Dict[str, Any]]:
    findings_meta = []
    muted_findings_ids = {m.finding.natural_key for m in muted_findings[: OOIList.HARD_LIMIT]}

    for finding in findings[: OOIList.HARD_LIMIT]:
        if finding.natural_key in muted_findings_ids:
            continue

        finding_type = get_finding_type_from_finding(finding)
        knowledge_base = get_knowledge_base_data_for_ooi(finding_type)
        severity = RiskLevelSeverity(knowledge_base["risk_level_severity"])
        if not severity_filter or severity in severity_filter:
            findings_meta.append(
                {
                    "finding_number": 0,
                    "finding": finding,
                    "finding_type": finding_type,
                    "severity": severity.value.capitalize(),
                    "risk_level_score": knowledge_base["risk_level_score"],
                }
            )

    return sort_by_severity_desc(findings_meta)


class FindingListView(BreadcrumbsMixin, BaseOOIListView, OrganizationView):
    template_name = "findings/finding_list.html"
    ooi_types = {Finding}
    paginate_by = 50

    def get_queryset(self):
        findings = super().get_queryset()
        muted_findings = OOIList(
            self.octopoes_api_connector,
            {MutedFinding},
            self.get_observed_at(),
            scan_level=DEFAULT_SCAN_LEVEL_FILTER,
            scan_profile_type=DEFAULT_SCAN_PROFILE_TYPE_FILTER,
        )
        severity_filter = []

        for severity in self.request.GET.getlist("severity"):
            try:
                severity_filter.append(RiskLevelSeverity(severity))
            except ValueError as e:
                messages.error(self.request, _(str(e)))

        try:
            return generate_findings_metadata(findings, muted_findings, severity_filter)
        except ConnectorException:
            messages.add_message(
                self.request, messages.ERROR, _("Failed to get list of findings, check server logs for more details.")
            )
            logger.exception("Failed get list of findings")
            return []

    def build_breadcrumbs(self):
        return [
            {
                "url": reverse_lazy("finding_list", kwargs={"organization_code": self.organization.code}),
                "text": _("Findings"),
            }
        ]


class Top10FindingListView(FindingListView):
    template_name = "findings/finding_list.html"
    ooi_types = {Finding}

    def get_queryset(self):
        return super().get_queryset()[:10]

    def build_breadcrumbs(self):
        return [
            {
                "url": reverse_lazy("organization_crisis_room", kwargs={"organization_code": self.organization.code}),
                "text": _("Crisis room"),
            }
        ]
