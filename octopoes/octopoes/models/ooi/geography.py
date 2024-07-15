from typing import Literal

from octopoes.models import OOI, Reference
from octopoes.models.persistence import ReferenceField


class GeographicPoint(OOI):
    object_type: Literal["GeographicPoint"] = "GeographicPoint"

    ooi: Reference = ReferenceField(OOI)

    longitude: float
    latitude: float

    @property
    def natural_key(self) -> str:
        return f"{str(self.ooi)}|{self.longitude}|{self.latitude}"
