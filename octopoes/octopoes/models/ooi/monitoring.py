from typing import Any, Literal

from octopoes.models import OOI, Reference
from octopoes.models.persistence import ReferenceField


class Application(OOI):
    object_type: Literal["Application"] = "Application"
    name: str

    _natural_key_attrs = ["name"]


class Incident(OOI):
    object_type: Literal["Incident"] = "Incident"

    application: Reference = ReferenceField(Application)
    event_id: str
    event_type: str
    event_title: str
    severity: str
    meta_data: dict[str, Any]

    _natural_key_attrs = ["application", "event_id"]
