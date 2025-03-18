from datetime import datetime
from typing import Any

from django.utils.translation import gettext_lazy as _

from octopoes.models import Reference
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.findings import Finding
from octopoes.models.ooi.service import IPService, TLSCipher
from reports.report_types.definitions import Report

CIPHER_FINDINGS = ["KAT-RECOMMENDATION-BAD-CIPHER", "KAT-MEDIUM-BAD-CIPHER", "KAT-CRITICAL-BAD-CIPHER"]
TREE_DEPTH = 3


class TLSReport(Report):
    id = "tls-report"
    name = _("TLS Report")
    description: str = _("TLS Report assesses the security of data encryption and transmission protocols.")
    plugins = {"required": {"testssl-sh-ciphers"}, "optional": set()}
    input_ooi_types = {IPService, Hostname}
    template_path = "tls_report/report.html"
    label_style = "3-light"

    def generate_data(self, input_ooi: str, valid_time: datetime) -> dict[str, Any]:
        results = {}
        class_type = Reference.from_str(input_ooi).class_type
        if class_type == Hostname:
            tree = self.octopoes_api_connector.get_tree(
                Reference.from_str(input_ooi), valid_time=valid_time, depth=6, types={IPService}
            ).store
            oois = [ooi for pk, ooi in tree.items() if ooi.ooi_type == "IPService"]
        else:
            oois = [input_ooi]
        for ooi in oois:
            suites: dict = {}
            findings: list[Finding] = []
            suites_with_findings = []
            ref = Reference.from_str(ooi)
            tree = self.octopoes_api_connector.get_tree(
                ref, valid_time=valid_time, depth=TREE_DEPTH, types={TLSCipher, Finding}
            ).store
            for pk, ooi in tree.items():
                if ooi.ooi_type == "TLSCipher":
                    suites = ooi.suites
                if ooi.ooi_type == "Finding" and ooi.finding_type.tokenized.id in CIPHER_FINDINGS:
                    findings.append(ooi)

            for protocol, cipher_suites in suites.items():
                for suite in cipher_suites:
                    for finding in findings:
                        if finding.description and suite["cipher_suite_name"] in finding.description:
                            suites_with_findings.append(suite["cipher_suite_name"])

            results[ooi] = {
                "input_ooi": ooi,
                "suites": suites,
                "findings": findings,
                "suites_with_findings": suites_with_findings,
            }
        return results
