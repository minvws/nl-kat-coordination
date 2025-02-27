from typing import Literal

from octopoes.models import OOI, Reference


class ExternalScan(OOI):
    object_type: Literal["ExternalScan"] = "ExternalScan"

    name: str

    _natural_key_attrs = ["name"]
    _information_value = ["name"]
    _traversable = False

    @classmethod
    def format_reference_human_readable(cls, reference: Reference) -> str:
        return reference.tokenized.name
