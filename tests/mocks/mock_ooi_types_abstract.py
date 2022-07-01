from typing import Literal

from octopoes.models import OOI, Reference
from octopoes.models.persistence import ReferenceField


class A(OOI):
    object_type: Literal["A"] = "A"
    id: str
    _natural_key_attrs = ["idname"]


class B(OOI):
    object_type: Literal["B"] = "B"
    a_ref: Reference = ReferenceField(A, max_issue_scan_level=1)
    id: str
    _natural_key_attrs = ["name"]
