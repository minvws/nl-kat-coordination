from typing import Literal, Optional

from octopoes.models import OOI, Reference
from octopoes.models.persistence import ReferenceField


class Software(OOI):
    object_type: Literal["Software"] = "Software"

    name: Optional[str]
    version: Optional[str]
    cpe: Optional[str]

    _natural_key_attrs = ["name", "version", "cpe"]
    _information_value = ["name"]
    _traversable = False

    @classmethod
    def format_reference_human_readable(cls, reference: Reference) -> str:
        version = reference.tokenized.version
        if version != "":
            version = f" {version}"
        return f"{reference.tokenized.name}{version}"


class SoftwareInstance(OOI):
    object_type: Literal["SoftwareInstance"] = "SoftwareInstance"

    ooi: Reference = ReferenceField(OOI, max_issue_scan_level=0, max_inherit_scan_level=1)
    software: Reference = ReferenceField(Software, max_issue_scan_level=1, max_inherit_scan_level=0)

    _natural_key_attrs = ["ooi", "software"]
    _reverse_relation_names = {"ooi": "software_instances", "software": "instances"}

    # PK example: SoftwareInstance|IPAddressV4|internet|1.1.1.1|Software|apache|1.0|apache:/a.2.1./asd/
    @property
    def natural_key(self) -> str:
        return f"{self.ooi}|{self.software}"

    @classmethod
    def format_reference_human_readable(cls, reference: Reference) -> str:
        parts = reference.natural_key.split("|")
        ooi_reference = Reference.from_str("|".join(parts[0:-4]))
        software_reference = Reference.from_str("|".join(parts[-4:]))
        return f"{software_reference.human_readable} @ {ooi_reference.human_readable}"
