from typing import List, Literal

from pydantic import BaseModel
from sqlalchemy.orm.query import Query


class FilterRequest(BaseModel):
    filter: List["Filter"]

class Filter(BaseModel):
    field: str
    node: str
    operator: Literal["@>", "<@", "@?", "@"]
    value: str

def apply_filter(query: Query, filter_request: FilterRequest):
    query = query.where()
    return query
