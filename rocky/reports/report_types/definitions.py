from logging import getLogger
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple, Type

from octopoes.models import OOI, Reference
from reports.report_types import DNSReport, TLSReport

REPORTS_DIR = Path(__file__).parent
logger = getLogger(__name__)
REPORTS = [DNSReport, TLSReport]


class Report:
    name: str
    required_boefjes: List
    optional_boefjes: List
    input_ooi_types: Set[Type[OOI]]
    html_template_path: str = "report.html"

    def __init__(self, octopoes_api_connector):
        self.octopoes_api_connector = octopoes_api_connector

    def generate_data(self, input_ooi: OOI) -> Tuple[Dict[str, str], str]:
        return NotImplementedError

    def render_report(self, data: Any) -> str:
        return NotImplementedError


def get_ooi_types_with_report() -> Set[Type[OOI]]:
    """
    Get all OOI types that have a report
    """
    return {ooi_type for report in REPORTS for ooi_type in report.input_ooi_types}


def get_report_types_for_ooi(ooi_pk: str) -> List[Type[Report]]:
    """
    Get all report types that can be generated for a given OOI
    """
    reference = Reference.from_str(ooi_pk)
    ooi_type = reference.class_type
    return [report for report in REPORTS if ooi_type in report.input_ooi_types]


def get_report_types_for_oois(ooi_pks: List[str]) -> Set[Type[Report]]:
    """
    Get all report types that can be generated for a given list of OOIs
    """
    return {report for ooi_pk in ooi_pks for report in get_report_types_for_ooi(ooi_pk)}
