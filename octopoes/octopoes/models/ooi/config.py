from typing import Literal

from octopoes.models import OOI, Reference
from octopoes.models.persistence import ReferenceField


class Config(OOI):
    object_type: Literal["Config"] = "Config"

    ooi: Reference = ReferenceField(OOI)
    bit_id: str
    config: str

    @property
    def natural_key(self) -> str:
        return str(self.ooi)

    @classmethod
    def format_reference_human_readable(cls, reference: Reference) -> str:
        parts = reference.natural_key.split("|")
        ooi_reference = Reference.from_str("|".join(parts))
        return f"Config of {ooi_reference.human_readable}"
