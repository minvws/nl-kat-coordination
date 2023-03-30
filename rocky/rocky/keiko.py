import re
import time
from typing import Dict, BinaryIO, List, Optional, Any
from http import HTTPStatus

import requests
from requests import HTTPError

from datetime import datetime, timezone
from django.conf import settings

from octopoes.models import OOI
from octopoes.models.ooi.findings import Finding, FindingType

from rocky.health import ServiceHealth
from rocky.exceptions import RockyError

from tools.ooi_helpers import (
    get_ooi_dict,
    get_knowledge_base_data_for_ooi_store,
    get_knowledge_base_data_for_ooi,
    get_finding_type_from_finding,
    RiskLevelSeverity,
)


class ReportException(RockyError):
    pass


class ReportNotFoundException(ReportException):
    pass


class GeneratingReportFailed(ReportException):
    pass


class KeikoClient:
    def __init__(self, base_uri: str):
        self.session = requests.Session()
        self._base_uri = base_uri

    def generate_report(self, template: str, data: Dict, glossary: str) -> str:
        try:
            res = self.session.post(
                f"{self._base_uri}/reports",
                json={
                    "template": template,
                    "data": data,
                    "glossary": glossary,
                },
            )
            res.raise_for_status()
        except HTTPError as e:
            raise GeneratingReportFailed from e

        return res.json()["report_id"]

    def get_report(self, report_id: str) -> BinaryIO:
        # try max 15 times to get the report, 1 second interval
        try:
            for _ in range(15):
                time.sleep(1)
                res = self.session.get(f"{self._base_uri}/reports/{report_id}.keiko.pdf", stream=True)

                if res.status_code == HTTPStatus.NOT_FOUND:
                    continue

                res.raise_for_status()
                return res.raw
        except HTTPError as e:
            raise GeneratingReportFailed from e

        raise ReportNotFoundException

    def health(self) -> ServiceHealth:
        res = self.session.get(f"{self._base_uri}/health")
        res.raise_for_status()

        return ServiceHealth.parse_obj(res.json())


keiko_client = KeikoClient(settings.KEIKO_API)


class ReportsService:
    FILE_NAME_FRIENDLY_DATE_FORMAT = "%Y_%d_%mT%H_%M_%S_%f_%z"

    def __init__(self, keiko_client: KeikoClient):
        self.keiko_client = keiko_client

    def get_report(
        self,
        valid_time: datetime,
        source_type: str,
        source_value: str,
        store: Dict,
    ) -> BinaryIO:
        report_data = build_findings_list_from_store(store)  # reuse existing dict structure
        report_data["findings_grouped"] = _ooi_field_as_string(report_data["findings_grouped"], store)
        report_data["valid_time"] = str(valid_time)
        report_data["report_source_type"] = source_type
        report_data["report_source_value"] = source_value

        report_id = self.keiko_client.generate_report("bevindingenrapport", report_data, "dutch.hiero.csv")

        return self.keiko_client.get_report(report_id)

    def get_organization_finding_report(
        self,
        valid_time: datetime,
        organization_name: str,
        findings_metadata: List[Dict[str, Any]],
    ) -> BinaryIO:
        findings = [item["finding"] for item in findings_metadata]
        store = {finding.primary_key: finding for finding in findings}

        return self.get_report(valid_time, "Organisatie", organization_name, store)

    @classmethod
    def ooi_report_file_name(cls, valid_time: datetime, organization_code: str, ooi_id: str):
        report_file_name = "_".join(
            [
                "bevindingenrapport",
                "nl",
                organization_code,
                ooi_id,
                valid_time.strftime(cls.FILE_NAME_FRIENDLY_DATE_FORMAT),
                datetime.now(timezone.utc).strftime(cls.FILE_NAME_FRIENDLY_DATE_FORMAT),
            ]
        )
        # allow alphanumeric characters, dashes and underscores, replace rest with underscores
        report_file_name = re.sub("[^\\w\\+-]", "_", report_file_name)
        report_file_name = f"{report_file_name}.pdf"

        return report_file_name

    @classmethod
    def organization_report_file_name(cls, organization_code: str):
        file_name = "_".join(
            [
                "bevindingenrapport_nl",
                organization_code,
                datetime.now(timezone.utc).strftime(cls.FILE_NAME_FRIENDLY_DATE_FORMAT),
            ]
        )

        return f"{file_name}.pdf"


def _ooi_field_as_string(findings_grouped: Dict, store: Dict):
    new_findings_grouped = {}

    for finding_type, finding_group in findings_grouped.items():
        list_of_findings = []
        for finding in finding_group["list"]:
            # Either take the human_readable or the primary key of the OOI from the Finding in the store
            if finding["ooi"]:
                ooi_field = str(finding["ooi"]["human_readable"])
            else:
                ooi_field = str(store[finding["id"]].ooi)

            list_of_findings.append({**finding, "ooi": ooi_field})

        new_findings_grouped[finding_type] = {
            "list": list_of_findings,
            "finding_type": finding_group["finding_type"],
        }

    return new_findings_grouped


def build_findings_list_from_store(ooi_store: Dict, finding_filter: Optional[List[str]] = None) -> Dict:
    knowledge_base = get_knowledge_base_data_for_ooi_store(ooi_store)

    findings = [
        build_finding_dict(finding_ooi, ooi_store, knowledge_base)
        for finding_ooi in ooi_store.values()
        if isinstance(finding_ooi, Finding)
    ]

    if finding_filter is not None:
        findings = [finding for finding in findings if finding["finding_type"]["id"] in finding_filter]

    findings = sorted(findings, key=lambda k: k["finding_type"]["risk_level_score"], reverse=True)

    findings_grouped = {}
    for finding in findings:
        if finding["finding_type"]["id"] not in findings_grouped:
            findings_grouped[finding["finding_type"]["id"]] = {
                "finding_type": finding["finding_type"],
                "list": [],
            }

        findings_grouped[finding["finding_type"]["id"]]["list"].append(finding)

    return {
        "meta": build_meta(findings),
        "findings_grouped": findings_grouped,
    }


def build_finding_dict(
    finding_ooi: Finding,
    ooi_store: Dict[str, OOI],
    knowledge_base: Dict,
) -> Dict:
    finding_dict = get_ooi_dict(finding_ooi)

    finding_type_ooi = get_finding_type_from_finding(finding_ooi)

    knowledge_base.update({finding_type_ooi.get_information_id(): get_knowledge_base_data_for_ooi(finding_type_ooi)})

    finding_type_dict = build_finding_type_dict(finding_type_ooi, knowledge_base)

    finding_dict["ooi"] = get_ooi_dict(ooi_store[str(finding_ooi.ooi)]) if str(finding_ooi.ooi) in ooi_store else None
    finding_dict["finding_type"] = finding_type_dict

    if finding_dict["description"] is None:
        finding_dict["description"] = finding_type_dict["description"]

    return finding_dict


def build_meta(findings: List[Dict]) -> Dict:
    meta = {
        "total": len(findings),
        "total_by_severity": {
            RiskLevelSeverity.CRITICAL.value: 0,
            RiskLevelSeverity.HIGH.value: 0,
            RiskLevelSeverity.MEDIUM.value: 0,
            RiskLevelSeverity.LOW.value: 0,
            RiskLevelSeverity.NONE.value: 0,
        },
        "total_by_finding_type": {},
        "total_finding_types": 0,
        "total_by_severity_per_finding_type": {
            RiskLevelSeverity.CRITICAL.value: 0,
            RiskLevelSeverity.HIGH.value: 0,
            RiskLevelSeverity.MEDIUM.value: 0,
            RiskLevelSeverity.LOW.value: 0,
            RiskLevelSeverity.NONE.value: 0,
        },
    }

    finding_type_ids = []
    for finding in findings:
        finding_type_id = finding["finding_type"]["id"]
        severity = finding["finding_type"]["risk_level_severity"]

        meta["total_by_severity"][severity] = meta["total_by_severity"].get(severity, 0) + 1
        meta["total_by_finding_type"][finding_type_id] = meta["total_by_finding_type"].get(finding_type_id, 0) + 1

        # count and append finding type id if not already present
        if finding_type_id not in finding_type_ids:
            finding_type_ids.append(finding_type_id)
            meta["total_by_severity_per_finding_type"][severity] = (
                meta["total_by_severity_per_finding_type"].get(severity, 0) + 1
            )
            meta["total_finding_types"] += 1

    return meta


def build_finding_type_dict(finding_type_ooi: FindingType, knowledge_base: Dict) -> Dict:
    finding_type_dict = get_ooi_dict(finding_type_ooi)

    if knowledge_base[finding_type_ooi.get_information_id()]:
        finding_type_dict.update(knowledge_base[finding_type_ooi.get_information_id()])

    finding_type_dict["findings"] = []

    return finding_type_dict
