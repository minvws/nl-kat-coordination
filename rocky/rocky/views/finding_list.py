from typing import Any, Dict, List, Optional

from django.contrib import messages
from django.urls.base import reverse_lazy
from django.utils.translation import gettext_lazy as _
from octopoes.models.ooi.findings import Finding

from rocky.views.mixins import OOIList
from rocky.views.ooi_view import BaseOOIListView
from tools.view_helpers import BreadcrumbsMixin
from tools.ooi_helpers import get_finding_type_from_finding, get_knowledge_base_data_for_ooi, RiskLevelSeverity
from account.mixins import OrganizationView


def sort_by_severity_desc(findings) -> List[Dict[str, Any]]:
    return sorted(findings, key=lambda x: x["risk_level_score"], reverse=True)


def generate_findings_metadata(
    findings: OOIList, severity_filter: Optional[List[RiskLevelSeverity]] = None
) -> List[Dict[str, Any]]:
    findings_meta = []

    for finding in findings[: OOIList.HARD_LIMIT]:
        finding_type = get_finding_type_from_finding(finding)
        knowledge_base = get_knowledge_base_data_for_ooi(finding_type)
        severity = RiskLevelSeverity(knowledge_base["risk_level_severity"])
        if not severity_filter or severity in severity_filter:
            findings_meta.append(
                {
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
        severity_filter = []

        for severity in self.request.GET.getlist("severity"):
            try:
                severity_filter.append(RiskLevelSeverity(severity))
            except ValueError as e:
                messages.error(self.request, _(str(e)))

        return generate_findings_metadata(findings, severity_filter)

    def build_breadcrumbs(self):
        return [
            {
                "url": reverse_lazy("finding_list", kwargs={"organization_code": self.organization.code}),
                "text": _("Findings"),
            }
        ]
