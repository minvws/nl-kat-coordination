from typing import Dict, List, Set, Type, Optional

from django.contrib import messages
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from octopoes.models import OOI
from octopoes.models.ooi.dns.records import (
    DNSARecord,
    DNSAAAARecord,
    DNSMXRecord,
    DNSNSRecord,
    DNSSOARecord,
)
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.findings import (
    Finding,
    FindingType,
)

from rocky.katalogus import get_katalogus
from rocky.views.ooi_view import BaseOOIDetailView, OOIBreadcrumbsMixin
from tools.forms import OOIReportSettingsForm
from tools.models import Organization
from tools.ooi_helpers import (
    get_ooi_dict,
    get_knowledge_base_data_for_ooi_store,
    get_knowledge_base_data_for_ooi,
    get_finding_type_from_finding,
    RiskLevelSeverity,
)
from tools.view_helpers import get_ooi_url


def build_meta(findings: List[Dict]) -> Dict:
    meta = {
        "total": len(findings),
        "total_by_severity": {
            RiskLevelSeverity.CRITICAL.value: 0,
            RiskLevelSeverity.HIGH.value: 0,
            RiskLevelSeverity.MEDIUM.value: 0,
            RiskLevelSeverity.LOW.value: 0,
            RiskLevelSeverity.NONE.value: 0,
        },
        "total_by_finding_type": {},
        "total_finding_types": 0,
        "total_by_severity_per_finding_type": {
            RiskLevelSeverity.CRITICAL.value: 0,
            RiskLevelSeverity.HIGH.value: 0,
            RiskLevelSeverity.MEDIUM.value: 0,
            RiskLevelSeverity.LOW.value: 0,
            RiskLevelSeverity.NONE.value: 0,
        },
    }

    finding_type_ids = []
    for finding in findings:
        finding_type_id = finding["finding_type"]["id"]
        severity = finding["finding_type"]["risk_level_severity"]

        meta["total_by_severity"][severity] = (
            meta["total_by_severity"].get(severity, 0) + 1
        )
        meta["total_by_finding_type"][finding_type_id] = (
            meta["total_by_finding_type"].get(finding_type_id, 0) + 1
        )

        # count and append finding type id if not already present
        if finding_type_id not in finding_type_ids:
            finding_type_ids.append(finding_type_id)
            meta["total_by_severity_per_finding_type"][severity] = (
                meta["total_by_severity_per_finding_type"].get(severity, 0) + 1
            )
            meta["total_finding_types"] += 1

    return meta


def build_finding_dict(
    finding_ooi: Finding,
    ooi_store: Dict[str, OOI],
    knowledge_base: Dict,
) -> Dict:
    finding_dict = get_ooi_dict(finding_ooi)

    finding_type_ooi = get_finding_type_from_finding(finding_ooi)

    knowledge_base.update(
        {
            finding_type_ooi.get_information_id(): get_knowledge_base_data_for_ooi(
                finding_type_ooi
            )
        }
    )

    finding_type_dict = build_finding_type_dict(finding_type_ooi, knowledge_base)

    finding_dict["ooi"] = (
        get_ooi_dict(ooi_store[str(finding_ooi.ooi)])
        if str(finding_ooi.ooi) in ooi_store
        else None
    )
    finding_dict["finding_type"] = finding_type_dict

    return finding_dict


def build_finding_type_dict(
    finding_type_ooi: FindingType, knowledge_base: Dict
) -> Dict:
    finding_type_dict = get_ooi_dict(finding_type_ooi)

    if knowledge_base[finding_type_ooi.get_information_id()]:
        finding_type_dict.update(knowledge_base[finding_type_ooi.get_information_id()])

    finding_type_dict["findings"] = []

    return finding_type_dict


def build_findings_list_from_store(
    ooi_store: Dict, finding_filter: Optional[List[str]] = None
) -> Dict:
    knowledge_base = get_knowledge_base_data_for_ooi_store(ooi_store)

    findings = [
        build_finding_dict(finding_ooi, ooi_store, knowledge_base)
        for finding_ooi in ooi_store.values()
        if isinstance(finding_ooi, Finding)
    ]

    if finding_filter is not None:
        findings = [
            finding
            for finding in findings
            if finding["finding_type"]["id"] in finding_filter
        ]

    findings = sorted(
        findings, key=lambda k: k["finding_type"]["risk_level_score"], reverse=True
    )

    findings_grouped = {}
    for finding in findings:
        if finding["finding_type"]["id"] not in findings_grouped:
            findings_grouped[finding["finding_type"]["id"]] = {
                "finding_type": finding["finding_type"],
                "list": [],
            }

        findings_grouped[finding["finding_type"]["id"]]["list"].append(finding)

    return {
        "meta": build_meta(findings),
        "findings_grouped": findings_grouped,
    }


class OOIReportView(OOIBreadcrumbsMixin, BaseOOIDetailView):
    template_name = "oois/ooi_report.html"
    connector_form_class = OOIReportSettingsForm

    def dispatch(self, request, *args, **kwargs):
        if self.get_observed_at() > timezone.now():
            messages.error(
                request,
                _("You can't generate a report for an OOI on a date in the future."),
            )
            return redirect(get_ooi_url("ooi_report", self.request.GET.get("ooi_id")))
        return super().dispatch(request, *args, **kwargs)

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.depth = self.get_depth()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        findings_list = build_findings_list_from_store(self.tree.store)
        context["breadcrumbs"].append(
            {
                "url": get_ooi_url("ooi_report", self.ooi.primary_key),
                "text": _("Findings report"),
            }
        )
        context["observed_at_form"] = self.get_connector_form()
        context["findings_list"] = findings_list
        return context


"""
The new report
Generates report from a starting point OOI with a filtered set of it's sub OOI's
and a filtered set of findings belonging to those OOIs.

boefjes_required - Set of possible boefjes
boefjes_optional - Set of possible boefjes
start_ooi - OOI that is the starting point of the report
allowed_oois - Set of OOIs that are interesting for this specific report
allowed_finding_types - Set of finding types that are interesting for this report
"""


class Report:
    boefjes_required: Set = None  # type: ignore
    boefjes_optional: Set = None  # type: ignore
    start_ooi: OOI = None  # type: ignore
    allowed_ooi_types: List[Type[OOI]] = None  # type: ignore
    allowed_finding_types: List[str] = None  # type: ignore
    boefjes: List = []

    @classmethod
    def get_finding_filter(cls):
        return cls.allowed_finding_types

    @classmethod
    def get_ooi_type_filter(cls):
        return [ooi.get_ooi_type() for ooi in cls.allowed_ooi_types]

    @classmethod
    def get_boefjes(cls, organization: Organization):
        cls.boefjes = []

        katalogus_boefjes = get_katalogus(organization.code).get_boefjes()
        for boefje in katalogus_boefjes:
            if boefje.id in cls.boefjes_required:
                cls.add_boefje(boefje, True)
            elif boefje.id in cls.boefjes_optional:
                cls.add_boefje(boefje, False)

        return cls.boefjes

    @classmethod
    def add_boefje(cls, boefje, required):
        cls.boefjes.append({"id": boefje.id, "required": required, "boefje": boefje})


class DNSReport(Report):
    boefjes_required = {"dns-records", "dns-zone"}
    boefjes_optional = {"dns-sec"}
    allowed_ooi_types = [
        DNSARecord,
        DNSAAAARecord,
        DNSMXRecord,
        DNSNSRecord,
        DNSSOARecord,
        Hostname,
    ]
    allowed_finding_types = [
        "KAT-581",
        "KAT-NAMESERVER-NO-IPV6",
        "KAT-NAMESERVER-NO-TWO-IPV6",
    ]
