from typing import Literal
from pydantic import confloat
from octopoes.models import OOI, Reference
from octopoes.models.persistence import ReferenceField


class GeographicPoint(OOI):
    object_type: Literal["GeographicPoint"] = "GeographicPoint"

    ooi: Reference = ReferenceField(OOI)

    longitude: confloat(ge=-180.0, le=180.0)
    latitude: confloat(ge=-90.0, le=90.0)

    @property
    def natural_key(self) -> str:
        return f"{str(self.ooi)}|{self.longitude}|{self.latitude}"
