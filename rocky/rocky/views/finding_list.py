import logging
from typing import Any, Dict, List, Optional

from django.urls.base import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView
from tools.forms.base import ObservedAtForm
from tools.forms.findings import (
    FindingRiskScoreRangeForm,
    FindingSeverityMultiSelectForm,
    FindingTypesMultiSelectForm,
    MutedFindingSelectionForm,
)
from tools.view_helpers import BreadcrumbsMixin

from octopoes.models.ooi.findings import RiskLevelSeverity
from rocky.views.mixins import ConnectorFormMixin, FindingList, OctopoesView, SeveritiesMixin

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


class FindingListFilter(OctopoesView, ConnectorFormMixin, SeveritiesMixin, ListView):
    connector_form_class = ObservedAtForm

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.severities = self.get_severities()
        self.valid_time = self.get_observed_at()
        self.muted_findings = request.GET.get("muted_findings")
        self.finding_types = request.GET.getlist("finding_types", [])
        self.hydrate_risk_scores()

    def hydrate_risk_scores(self) -> None:
        risk_score_min = self.request.GET.get("risk_score_min", 0)
        risk_score_max = self.request.GET.get("risk_score_max", 10)
        if not risk_score_min:
            risk_score_min = 0
        if not risk_score_max:
            risk_score_max = 10
        self.risk_score_min = float(risk_score_min)
        self.risk_score_max = float(risk_score_max)

    def get_queryset(self) -> FindingList:
        return FindingList(
            octopoes_connector=self.octopoes_api_connector,
            valid_time=self.valid_time,
            severities=self.severities,
            risk_score_min=self.risk_score_min,
            risk_score_max=self.risk_score_max,
            exclude_muted=self.muted_findings == "exclude",
            show_muted=self.muted_findings == "show",
            finding_types=self.finding_types,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["observed_at_form"] = self.get_connector_form()
        context["severity_filter"] = FindingSeverityMultiSelectForm(self.request.GET)
        context["risk_score_filter"] = FindingRiskScoreRangeForm(self.request.GET)
        context["muted_findings_filter"] = MutedFindingSelectionForm(self.request.GET)
        context["finding_types_filter"] = FindingTypesMultiSelectForm(self.request.GET)
        return context


class FindingListView(BreadcrumbsMixin, FindingListFilter):
    template_name = "findings/finding_list.html"
    paginate_by = 2

    def build_breadcrumbs(self):
        return [
            {
                "url": reverse_lazy("finding_list", kwargs={"organization_code": self.organization.code}),
                "text": _("Findings"),
            }
        ]


class Top10FindingListView(FindingListView):
    template_name = "findings/finding_list.html"
    paginate_by = 10

    def build_breadcrumbs(self):
        return [
            {
                "url": reverse_lazy("organization_crisis_room", kwargs={"organization_code": self.organization.code}),
                "text": _("Crisis room"),
            }
        ]
