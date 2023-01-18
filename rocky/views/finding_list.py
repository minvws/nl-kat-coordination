from typing import Any, Dict, List
from django.urls.base import reverse_lazy
from django.utils.translation import gettext_lazy as _
from octopoes.models.ooi.findings import Finding
from rocky.views.ooi_view import BaseOOIListView
from tools.view_helpers import BreadcrumbsMixin
from tools.ooi_helpers import get_finding_type_from_finding, get_knowledge_base_data_for_ooi
from account.mixins import OrganizationView


def sort_by_severity_desc(findings) -> List[Dict[str, Any]]:
    return sorted(findings, key=lambda x: x["risk_level_score"], reverse=True)


class FindingListView(BreadcrumbsMixin, BaseOOIListView, OrganizationView):
    template_name = "findings/finding_list.html"
    ooi_types = {Finding}
    paginate_by = 50

    def get_queryset(self):
        findings = super().get_queryset()
        findings_meta = []
        severity_filter = self.request.GET.get("severity")

        for finding in findings[: findings.count]:
            finding_type = get_finding_type_from_finding(finding)
            knowledge_base = get_knowledge_base_data_for_ooi(finding_type)
            severity = knowledge_base["risk_level_severity"]
            if not severity_filter or severity_filter.lower() == severity.lower():
                findings_meta.append(
                    {
                        "finding": finding,
                        "finding_type": finding_type,
                        "severity": severity.capitalize(),
                        "risk_level_score": knowledge_base["risk_level_score"],
                    }
                )
        return sort_by_severity_desc(findings_meta)

    def build_breadcrumbs(self):
        return [
            {
                "url": reverse_lazy("finding_list", kwargs={"organization_code": self.organization.code}),
                "text": _("Findings"),
            }
        ]
