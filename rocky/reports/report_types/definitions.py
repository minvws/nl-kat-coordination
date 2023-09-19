import importlib
import pkgutil
from functools import lru_cache
from logging import getLogger
from pathlib import Path
from types import ModuleType
from typing import Dict, List, Set, Type

from pydantic import BaseModel

from octopoes.models import OOI

REPORTS_DIR = Path(__file__).parent
REPORT_ATTR_NAME = "REPORT"
logger = getLogger(__name__)


class ReportDefinition(BaseModel):
    name: str
    required_boefjes: List
    optional_boefjes: List
    input_ooi_types: Set[Type[OOI]]
    html_template_path: str = "report.html"

    def get_data(self):
        return NotImplementedError

    def generate_report(self):
        return NotImplementedError


@lru_cache(maxsize=32)
def get_reports() -> Dict[str, ReportDefinition]:
    report_definitions = {}

    for package in pkgutil.walk_packages([str(REPORTS_DIR)]):
        if package.name in ["definitions", "runner"]:
            continue

        try:
            module: ModuleType = importlib.import_module(".report", f"{REPORTS_DIR.name}.{package.name}")

            if hasattr(module, REPORT_ATTR_NAME):
                report_definition: ReportDefinition = getattr(module, REPORT_ATTR_NAME)
                report_definitions[report_definition.name] = report_definition

            else:
                logger.warning('module "%s" has no attribute %s', package.name, REPORT_ATTR_NAME)

        except ModuleNotFoundError:
            logger.warning('package "%s" has no module %s', package.name, "report")

    return report_definitions


def get_ooi_types_with_report() -> List[Type[OOI]]:
    oois = []
    for _, report in get_reports().values():
        for ooi_type in report.input_ooi_types:
            oois.append(ooi_type)
    return oois
