from typing import Dict, List, Set, Type

from octopoes.models import OOI, Reference
from reports.report_types.definitions import Report
from reports.report_types.dns_report.report import DNSReport
from reports.report_types.tls_report.report import TLSReport

REPORTS = [DNSReport, TLSReport]


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


def get_report_by_id(report_id: str) -> Type[Report]:
    """
    Get report type by id
    """
    for report in REPORTS:
        if report.id == report_id:
            return report
    raise ValueError(f"Report with id {report_id} not found")


def get_plugins_for_report_ids(reports: List[str]) -> Dict[str, List[str]]:
    """
    Get all boefjes that are required and optional for a given list of reports
    """
    required_boefjes = set()
    optional_boefjes = set()
    for report_id in reports:
        report = get_report_by_id(report_id)
        required_boefjes.update(report.required_boefjes)
        optional_boefjes.update(report.optional_boefjes)
    return {"required": list(required_boefjes), "optional": list(optional_boefjes)}


def generate_reports_for_oois(
    ooi_pks: List[str], report_types: List[str], octopoes_api_connector
) -> Dict[str, Dict[str, Dict[str, str]]]:
    report_data = {}
    for ooi in ooi_pks:
        report_data[str(ooi)] = {}
        for report in report_types:
            report = get_report_by_id(report)
            if Reference.from_str(ooi).class_type in report.input_ooi_types:
                data, template = report(octopoes_api_connector).generate_data(ooi)
                report_data[str(ooi)][report.name] = {"data": data, "template": template}
    return report_data
