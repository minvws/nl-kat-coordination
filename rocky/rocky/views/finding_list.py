from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any

import structlog
from django.urls.base import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView
from tools.forms.base import ObservedAtForm
from tools.forms.findings import FindingSeverityMultiSelectForm, MutedFindingSelectionForm
from tools.view_helpers import BreadcrumbsMixin

from octopoes.models.ooi.findings import RiskLevelSeverity
from rocky.views.mixins import ConnectorFormMixin, FindingList, OctopoesView, SeveritiesMixin

logger = structlog.get_logger(__name__)


def sort_by_severity_desc(findings) -> list[dict[str, Any]]:
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
    severity_filter: Iterable[RiskLevelSeverity] | None = None,
) -> list[dict[str, Any]]:
    findings_meta = []

    for finding in findings[: FindingList.HARD_LIMIT]:
        finding_type = finding.finding_type

        if not severity_filter or (finding_type.risk_severity and finding_type.risk_severity in severity_filter):
            findings_meta.append(
                {
                    "finding_number": 0,
                    "finding": finding,
                    "finding_type": finding_type,
                    "severity": finding_type.risk_severity.name if finding_type.risk_severity else "",
                    "risk_level_score": finding_type.risk_score,
                }
            )

    return sort_by_severity_desc(findings_meta)


class FindingListFilter(OctopoesView, ConnectorFormMixin, SeveritiesMixin, ListView):
    connector_form_class = ObservedAtForm

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.severities = self.get_severities()
        self.muted_findings = request.GET.get("muted_findings", "non-muted")

        self.exclude_muted = self.muted_findings == "non-muted"
        self.only_muted = self.muted_findings == "muted"

    def count_observed_at_filter(self) -> int:
        return 1 if datetime.now(timezone.utc).date() != self.observed_at.date() else 0

    def count_active_filters(self):
        return len(self.severities) + 1 if self.muted_findings else 0 + self.count_observed_at_filter()

    def get_queryset(self) -> FindingList:
        return FindingList(
            octopoes_connector=self.octopoes_api_connector,
            valid_time=self.observed_at,
            severities=self.severities,
            exclude_muted=self.exclude_muted,
            only_muted=self.only_muted,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["observed_at_form"] = self.get_connector_form()
        context["observed_at"] = self.observed_at
        context["severity_filter"] = FindingSeverityMultiSelectForm({"severity": list(self.severities)})
        context["muted_findings_filter"] = MutedFindingSelectionForm({"muted_findings": self.muted_findings})
        context["only_muted"] = self.only_muted
        context["active_filters_counter"] = self.count_active_filters()
        return context


class FindingListView(BreadcrumbsMixin, FindingListFilter):
    template_name = "findings/finding_list.html"
    paginate_by = 20

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
