"""Base models for keiko."""

from pydantic import BaseModel, Extra

from keiko.version import __version__

# pylint: disable=too-few-public-methods


class DataShapeBase(BaseModel):
    """Base model for data shapes."""

    keiko_version: str = __version__

    class Config:
        """Pydantic config for DataShapeBase."""

        extra = Extra.allow


class ReportArgumentsBase(BaseModel):
    """Base model for report arguments."""

    template: str
    data: DataShapeBase
    glossary: str
    debug: bool = False
