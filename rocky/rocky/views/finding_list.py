import logging
from typing import Any, Dict, List, Optional

from django.contrib import messages
from django.urls.base import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView
from tools.view_helpers import BreadcrumbsMixin

from octopoes.models.ooi.findings import Finding, RiskLevelSeverity
from rocky.views.mixins import FindingList, OctopoesView

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
    findings: FindingList,
    severity_filter: Optional[List[RiskLevelSeverity]] = None,
) -> List[Dict[str, Any]]:
    findings_meta = []

    for finding in findings[: FindingList.HARD_LIMIT]:
        finding_type = finding.finding_type

        if not severity_filter or finding_type.risk_severity in severity_filter:
            findings_meta.append(
                {
                    "finding_number": 0,
                    "finding": finding,
                    "finding_type": finding_type,
                    "severity": finding_type.risk_severity.name,
                    "risk_level_score": finding_type.risk_score,
                }
            )

    return sort_by_severity_desc(findings_meta)


class FindingListView(BreadcrumbsMixin, OctopoesView, ListView):
    template_name = "findings/finding_list.html"
    ooi_types = {Finding}
    paginate_by = 50

    def get_queryset(self) -> FindingList:
        severities = set()
        for severity in self.request.GET.getlist("severity"):
            try:
                severities.add(RiskLevelSeverity(severity))
            except ValueError as e:
                messages.error(self.request, _(str(e)))

        return FindingList(self.octopoes_api_connector, self.get_observed_at(), severities)[: FindingList.HARD_LIMIT]

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
