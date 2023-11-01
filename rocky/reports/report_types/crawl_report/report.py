from datetime import datetime
from logging import getLogger
from typing import Any, Dict

from django.utils.translation import gettext_lazy as _

from octopoes.models import Reference
from octopoes.models.ooi.web import CrawlInformation, HostnameHTTPURL
from reports.report_types.definitions import Report

logger = getLogger(__name__)

TREE_DEPTH = 1


class CrawlReport(Report):
    id = "crawl-report"
    name = _("Crawl report")
    description: str = _("Crawl reports show the hostname and cookies gathered when crawling a URL.")
    plugins = {"required": ["kat_chrome_mitmproxy", "kat_har_normalizer"], "optional": []}
    input_ooi_types = {HostnameHTTPURL}
    template_path = "crawl_report/report.html"

    def generate_data(self, input_ooi: str, valid_time: datetime) -> Dict[str, Any]:
        ref = Reference.from_str(input_ooi)
        tree = self.octopoes_api_connector.get_tree(
            ref, depth=TREE_DEPTH, types={CrawlInformation}, valid_time=valid_time
        ).store

        hostnames_and_cookies = None

        for ooi in tree.values():
            if ooi.ooi_type == "CrawlInformation":
                hostnames_and_cookies = dict(sorted(ooi.hostnames_and_cookies.items()))

        return {"input_ooi": input_ooi, "hostnames_and_cookies": hostnames_and_cookies}
