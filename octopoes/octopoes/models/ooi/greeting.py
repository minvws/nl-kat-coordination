from __future__ import annotations

from typing import Literal
from octopoes.models.persistence import ReferenceField
from octopoes.models.ooi.network import IPAddress
from octopoes.models import OOI, Reference

class Greeting(OOI):
    object_type: Literal["Greeting"] = "Greeting"

    greeting: str
    address: Reference = ReferenceField(IPAddress, max_issue_scan_level=0, max_inherit_scan_level=3 )

    _natural_key_attrs = ["greeting", "address"]



Greeting.model_rebuild()