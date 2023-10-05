from logging import getLogger

from django.utils.translation import gettext_lazy as _

from octopoes.models import Reference
from octopoes.models.ooi.findings import Finding
from octopoes.models.ooi.service import IPService, TLSCipher
from reports.report_types.definitions import Report

logger = getLogger(__name__)

CIPHER_FINDINGS = ["KAT-RECOMMENDATION-BAD-CIPHER", "KAT-MEDIUM-BAD-CIPHER", "KAT-CRITICAL-BAD-CIPHER"]


class TLSReport(Report):
    id = "tls-report"
    name = _("TLS Report")
    description: str = _("TLS reports assess the security of data encryption and transmission protocols.")
    plugins = {"required": ["testssl-sh-ciphers"], "optional": []}
    input_ooi_types = {IPService}
    html_template_path = "tls_report/report.html"
    tree_depth: int = 3

    def generate_data(self, input_ooi: str):
        suites = {}
        findings = []
        suites_with_findings = []
        ref = Reference.from_str(input_ooi)
        tree = self.octopoes_api_connector.get_tree(ref, depth=self.tree_depth, types={TLSCipher, Finding}).store
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
        }, self.html_template_path
