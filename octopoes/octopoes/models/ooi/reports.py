from datetime import datetime
from typing import Any, Literal
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


class BaseReport(OOI):
    name: str
    template: str | None = None
    date_generated: datetime

    organization_code: str
    organization_name: str
    organization_tags: list[str]
    data_raw_id: str

    observed_at: datetime
    report_recipe: Reference | None = ReferenceField("ReportRecipe", default=None)

    @classmethod
    def format_reference_human_readable(cls, reference: Reference) -> str:
        return f"Report {reference.tokenized.name}"


class Report(BaseReport):
    object_type: Literal["Report"] = "Report"
    report_type: Literal["concatenated-report", "aggregate-organisation-report", "multi-organization-report"]

    input_oois: list[str]

    _natural_key_attrs = ["report_recipe"]


class AssetReport(BaseReport):
    object_type: Literal["AssetReport"] = "AssetReport"
    report_type: str

    input_ooi: str

    _natural_key_attrs = ["input_ooi", "report_type"]


class ReportRecipe(OOI):
    object_type: Literal["ReportRecipe"] = "ReportRecipe"

    recipe_id: UUID

    report_name_format: str
    subreport_name_format: str | None = None

    input_recipe: dict[str, Any]  # can contain a query which maintains a live set of OOIs or manually picked OOIs.
    parent_report_type: str | None = None
    report_types: list[str]

    cron_expression: str

    _natural_key_attrs = ["recipe_id"]
