from datetime import datetime
from typing import Literal
from uuid import UUID

from octopoes.models import OOI, Reference
from octopoes.models.persistence import ReferenceField


class ReportData(OOI):
    object_type: Literal["ReportData"] = "ReportData"
    organization_code: str
    organization_name: str
    organization_tags: list[str]
    data: dict

    _natural_key_attrs = ["organization_code"]

    @classmethod
    def format_reference_human_readable(cls, reference: Reference) -> str:
        return f"Report data of organization {reference.tokenized.organization_code}"


class Report(OOI):
    name: str | None = None
    report_type: str | None = None
    template: str | None = None
    date_generated: datetime

    input_ooi: Reference | None = ReferenceField(OOI, max_issue_scan_level=1, max_inherit_scan_level=2, default=None)

    report_id: UUID

    object_type: Literal["Report"] = "Report"
    organization_code: str
    organization_name: str
    organization_tags: list[str]
    data_raw_id: str

    observed_at: datetime
    parent_report: Reference | None = ReferenceField(
        "Report", max_issue_scan_level=1, max_inherit_scan_level=2, default=None
    )
    has_parent: bool

    _natural_key_attrs = ["report_id"]

    @classmethod
    def format_reference_human_readable(cls, reference: Reference) -> str:
        return f"Report {reference.tokenized.report_id}"
