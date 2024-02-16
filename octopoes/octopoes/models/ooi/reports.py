from typing import Literal

from octopoes.models import OOI, Reference


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
