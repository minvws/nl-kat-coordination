from logging import getLogger
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple, Type

from octopoes.models import OOI

REPORTS_DIR = Path(__file__).parent
logger = getLogger(__name__)


class Report:
    id: str
    name: str
    description: str
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
