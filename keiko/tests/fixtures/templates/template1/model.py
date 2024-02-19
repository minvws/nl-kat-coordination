"""
Template1 Datamodel
"""

from pydantic import BaseModel

from keiko.base_models import DataShapeBase

# pylint: disable=missing-class-docstring


class SubModel(BaseModel):
    prop2: int


class Model(BaseModel):
    prop1: str
    sub_model: SubModel


class DataShape(DataShapeBase):
    models: list[Model]
