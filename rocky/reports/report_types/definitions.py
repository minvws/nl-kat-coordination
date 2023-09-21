import importlib
import inspect
import pkgutil
from logging import getLogger
from pathlib import Path
from types import ModuleType
from typing import List, Set, Type

from octopoes.models import OOI, Reference

REPORTS_DIR = Path(__file__).parent
logger = getLogger(__name__)


class Report:
    name: str
    required_boefjes: List
    optional_boefjes: List
    input_ooi_types: Set[Type[OOI]]
    html_template_path: str = "report.html"

    def get_data(self):
        return NotImplementedError

    def generate_report(self):
        return NotImplementedError


def get_reports() -> List:
    reports = []

    for package in pkgutil.walk_packages([str(REPORTS_DIR)]):
        if package.name in ["definitions"]:
            continue

        try:
            module: ModuleType = importlib.import_module(
                ".report", package=f"reports.{REPORTS_DIR.name}.{package.name}"
            )

            for name, obj in inspect.getmembers(module):
                # Check if the member is a class, is a subclass of Report, and is not Report itself
                if inspect.isclass(obj) and issubclass(obj, Report) and obj != Report:
                    reports.append(obj)

        except ModuleNotFoundError:
            logger.warning('package "%s" has no module %s', package.name, "report")

    return reports


def get_ooi_types_with_report() -> List[Type[OOI]]:
    return [ooi_type for report in get_reports() for ooi_type in report.input_ooi_types]


def get_report_types_for_ooi(ooi_pk: str) -> List[Type[Report]]:
    reference = Reference.from_str(ooi_pk)
    ooi_type = reference.class_type
    return [report for report in get_reports() if ooi_type in report.input_ooi_types]
