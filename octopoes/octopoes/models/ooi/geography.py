from typing import Annotated, Literal

from pydantic import Field

from octopoes.models import OOI, Reference
from octopoes.models.persistence import ReferenceField


class GeographicPoint(OOI):
    object_type: Literal["GeographicPoint"] = "GeographicPoint"

    ooi: Reference = ReferenceField(OOI)

    longitude: Annotated[float, Field(strict=True, ge=-180.0, le=180.0)]
    latitude: Annotated[float, Field(strict=True, ge=-180.0, le=180.0)]

    @property
    def natural_key(self) -> str:
        return f"{str(self.ooi)}|{self.longitude}|{self.latitude}"
