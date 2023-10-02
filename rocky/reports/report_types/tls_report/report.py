from logging import getLogger
from typing import List

from django.utils.translation import gettext_lazy as _

from octopoes.models import Reference
from octopoes.models.ooi.service import IPService, TLSCipher
from reports.report_types.definitions import Report

logger = getLogger(__name__)


class TLSReport(Report):
    id = "tls-report"
    name = _("TLS Report")
    description: str = _("TLS reports assess the security of data encryption and transmission protocols.")
    required_boefjes: List = []
    optional_boefjes: List = []
    input_ooi_types = {IPService}
    html_template_path = "tls_report/report.html"

    def generate_data(self, input_ooi: str):
        suites = {}
        ref = Reference.from_str(input_ooi)
        tree = self.octopoes_api_connector.get_tree(ref, depth=3, types={TLSCipher}).store
        for pk, ooi in tree.items():
            logger.error(pk)
            logger.error(ooi.ooi_type)
            if ooi.ooi_type == "TLSCipher":
                suites = ooi.suites

        return {
            "input_ooi": input_ooi,
            "suites": suites,
        }, self.html_template_path
