from datetime import datetime
from logging import getLogger
from pathlib import Path
from typing import Any, TypedDict

from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models.types import OOIType

REPORTS_DIR = Path(__file__).parent
logger = getLogger(__name__)


class ReportPlugins(TypedDict):
    required: list[str]
    optional: list[str]


class BaseReport:
    id: str
    name: str
    description: str
    template_path: str = "report.html"

    def __init__(self, octopoes_api_connector: OctopoesAPIConnector):
        self.octopoes_api_connector = octopoes_api_connector


class Report(BaseReport):
    plugins: ReportPlugins
    input_ooi_types: set[OOIType]

    def generate_data(self, input_ooi: str, valid_time: datetime) -> dict[str, Any]:
        raise NotImplementedError

    @classmethod
    def class_attributes(cls) -> dict[str, Any]:
        return {
            "id": cls.id,
            "name": cls.name,
            "description": cls.description,
            "plugins": cls.plugins,
            "input_ooi_types": cls.input_ooi_types,
            "template_path": cls.template_path,
        }


class MultiReport(BaseReport):
    plugins: ReportPlugins
    input_ooi_types: set[OOIType]

    def post_process_data(self, data: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class AggregateReportSubReports(TypedDict):
    required: list[type[Report] | type[MultiReport]]
    optional: list[type[Report] | type[MultiReport]]


class AggregateReport(BaseReport):
    reports: AggregateReportSubReports

    def post_process_data(self, data: dict[str, Any], valid_time: datetime) -> dict[str, Any]:
        raise NotImplementedError


class ReportType(TypedDict):
    id: str
    name: str
    description: str
