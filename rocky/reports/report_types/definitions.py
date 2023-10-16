from datetime import datetime
from logging import getLogger
from pathlib import Path
from typing import Dict, List, Set, Tuple, Type

from octopoes.models import OOI

REPORTS_DIR = Path(__file__).parent
logger = getLogger(__name__)


class Report:
    id: str
    name: str
    description: str
    plugins: Dict[str, List[str]]
    input_ooi_types: Set[Type[OOI]]
    html_template_path: str = "report.html"

    def __init__(self, octopoes_api_connector):
        self.octopoes_api_connector = octopoes_api_connector

    def generate_data(self, input_ooi: str, valid_time: Type[datetime]) -> Tuple[Dict[str, str], str]:
        raise NotImplementedError
