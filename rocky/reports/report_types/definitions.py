from collections.abc import Callable, Iterable
from datetime import datetime
from logging import getLogger
from pathlib import Path
from typing import Any, TypedDict, TypeVar

from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import OOI, Reference
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.network import IPAddressV4, IPAddressV6
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
    label_style = "1-light"  # default/fallback color

    def __init__(self, octopoes_api_connector: OctopoesAPIConnector):
        self.octopoes_api_connector = octopoes_api_connector


BaseReportType = TypeVar("BaseReportType", bound="BaseReport")


class Report(BaseReport):
    plugins: ReportPlugins
    input_ooi_types: set[type[OOI]]

    def generate_data(self, input_ooi: str, valid_time: datetime) -> dict[str, Any]:
        raise NotImplementedError

    def collect_data(self, input_oois: Iterable[str], valid_time: datetime) -> dict[str, dict[str, Any]]:
        """Generate data for multiple OOIs. Child classes can override this method to improve performance."""

        return {input_ooi: self.generate_data(input_ooi, valid_time) for input_ooi in input_oois}

    @classmethod
    def class_attributes(cls) -> dict[str, Any]:
        return {
            "id": cls.id,
            "name": cls.name,
            "description": cls.description,
            "plugins": cls.plugins,
            "input_ooi_types": cls.input_ooi_types,
            "template_path": cls.template_path,
            "label_style": cls.label_style,
        }

    @staticmethod
    def group_by_source(
        query_result: list[tuple[str, OOIType]],
        check: Callable[[OOIType], bool] | None = None,
    ) -> dict[str, list[OOIType]]:
        """Transform a query-many result from [(ref1, obj1), (ref1, obj2), ...] into {ref1: [obj1, obj2], ...}"""

        result: dict[str, list[OOIType]] = {}

        for source, ooi in query_result:
            if source not in result:
                result[source] = []

            if not check or check(ooi):
                result[source].append(ooi)

        return result

    @staticmethod
    def group_finding_types_by_source(
        query_result: list[tuple[str, OOIType]],
        keep_ids: list[str] | None = None,
    ) -> dict[str, list[OOIType]]:
        if keep_ids:
            return Report.group_by_source(query_result, lambda x: x.id in keep_ids)

        return Report.group_by_source(query_result)

    def to_hostnames(self, input_oois: Iterable[str], valid_time: datetime) -> dict[str, list[Reference]]:
        """
        Turn a list of either Hostname and IPAddress references into a list of related hostnames, grouped by input ooi.

        If an input ooi is an IP without hostnames, the key will still be present but the list will be empty.
        """

        refs = [Reference.from_str(input_ooi) for input_ooi in input_oois]

        hostnames_by_input_ooi = {str(ref): [ref] if ref.class_type == Hostname else [] for ref in refs}
        ip_refs = [ref for ref in refs if ref.class_type in (IPAddressV4, IPAddressV6)]

        for input_ooi, ip_hostname in self.octopoes_api_connector.query_many(
            "IPAddress.<address[is ResolvedHostname].hostname", valid_time, ip_refs
        ):
            if input_ooi not in hostnames_by_input_ooi:
                hostnames_by_input_ooi[input_ooi] = []

            hostnames_by_input_ooi[input_ooi].append(ip_hostname.reference)

        return hostnames_by_input_ooi

    def to_ips(self, input_oois: Iterable[str], valid_time: datetime) -> dict[str, list[Reference]]:
        """
        Turn a list of either Hostname and IPAddress reference strings into a list of related ips.

        If an input ooi is a Hostname without ips, the key will still be present but the list will be empty.
        """

        refs = [Reference.from_str(input_ooi) for input_ooi in input_oois]

        ips_by_input_ooi = {str(ref): [ref] if ref.class_type in [IPAddressV4, IPAddressV6] else [] for ref in refs}
        hostname_refs = [ref for ref in refs if ref.class_type == Hostname]

        for input_ooi, hostname_ip in self.octopoes_api_connector.query_many(
            "Hostname.<hostname[is ResolvedHostname].address", valid_time, hostname_refs
        ):
            if input_ooi not in ips_by_input_ooi:
                ips_by_input_ooi[input_ooi] = []

            ips_by_input_ooi[input_ooi].append(hostname_ip.reference)

        return ips_by_input_ooi


class MultiReport(BaseReport):
    plugins: ReportPlugins
    input_ooi_types: set[type[OOI]]

    def post_process_data(self, data: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class AggregateReportSubReports(TypedDict):
    required: list[type[Report]]
    optional: list[type[Report]]


class AggregateReport(BaseReport):
    reports: AggregateReportSubReports

    def post_process_data(self, data: dict[str, Any], valid_time: datetime) -> dict[str, Any]:
        raise NotImplementedError


class ReportType(TypedDict):
    id: str
    name: str
    description: str
    label_style: str
