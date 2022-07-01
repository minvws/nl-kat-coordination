from typing import Optional, Literal

from octopoes.models import OOI, Reference
from octopoes.models.persistence import ReferenceField


# todo: make abstract
class FindingType(OOI):
    id: str

    _natural_key_attrs = ["id"]
    _information_value = ["id"]
    _traversable = False

    @classmethod
    def format_reference_human_readable(cls, reference: Reference) -> str:
        return reference.tokenized.id


class CVEFindingType(FindingType):
    object_type: Literal["CVEFindingType"] = "CVEFindingType"


class CWEFindingType(FindingType):
    object_type: Literal["CWEFindingType"] = "CWEFindingType"


class RetireJSFindingType(FindingType):
    object_type: Literal["RetireJSFindingType"] = "RetireJSFindingType"


class SnykFindingType(FindingType):
    object_type: Literal["SnykFindingType"] = "SnykFindingType"


class KATFindingType(FindingType):
    object_type: Literal["KATFindingType"] = "KATFindingType"


class Finding(OOI):
    object_type: Literal["Finding"] = "Finding"

    finding_type: Reference = ReferenceField(FindingType)
    ooi: Reference = ReferenceField(OOI)
    proof: Optional[str]
    description: Optional[str]
    reproduce: Optional[str]

    @property
    def natural_key(self) -> str:
        return f"{str(self.ooi)}|{self.finding_type.natural_key}"

    _reverse_relation_names = {"ooi": "findings", "finding_type": "instances"}

    @classmethod
    def format_reference_human_readable(cls, reference: Reference) -> str:
        parts = reference.natural_key.split("|")
        finding_type = parts.pop()
        ooi_reference = Reference.from_str("|".join(parts))
        return f"{finding_type} @ {ooi_reference.human_readable}"
