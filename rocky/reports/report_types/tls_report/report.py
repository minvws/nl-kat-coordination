from datetime import datetime
from logging import getLogger
from typing import Any, Dict

from django.utils.translation import gettext_lazy as _

from octopoes.models import Reference
from octopoes.models.ooi.findings import Finding
from octopoes.models.ooi.service import IPService, TLSCipher
from reports.report_types.definitions import Report

logger = getLogger(__name__)

CIPHER_FINDINGS = ["KAT-RECOMMENDATION-BAD-CIPHER", "KAT-MEDIUM-BAD-CIPHER", "KAT-CRITICAL-BAD-CIPHER"]
TREE_DEPTH = 3


class TLSReport(Report):
    id = "tls-report"
    name = _("TLS Report")
    description: str = _("TLS reports assess the security of data encryption and transmission protocols.")
    plugins = {"required": ["testssl-sh-ciphers"], "optional": []}
    input_ooi_types = {IPService}
    template_path = "tls_report/report.html"

    def generate_data(self, input_ooi: str, valid_time: datetime) -> Dict[str, Any]:
        suites = {}
        findings = []
        suites_with_findings = []
        ref = Reference.from_str(input_ooi)
        tree = self.octopoes_api_connector.get_tree(
            ref, depth=TREE_DEPTH, types={TLSCipher, Finding}, valid_time=valid_time
        ).store
        for pk, ooi in tree.items():
            if ooi.ooi_type == "TLSCipher":
                suites = ooi.suites
            if ooi.ooi_type == "Finding" and ooi.finding_type.tokenized.id in CIPHER_FINDINGS:
                findings.append(ooi)

        for protocol, cipher_suites in suites.items():
            for suite in cipher_suites:
                for finding in findings:
                    if suite["cipher_suite_name"] in finding.description:
                        suites_with_findings.append(suite["cipher_suite_name"])

        return {
            "input_ooi": input_ooi,
            "suites": suites,
            "findings": findings,
            "suites_with_findings": suites_with_findings,
        }
