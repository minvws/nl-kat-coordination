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

# TODO: implement and, or, not
def apply_filter(entity, query: Query, filter_request: FilterRequest):
    # What is the json column to filter on?
    # Get field of entity to do models.TaskDB.p_item (the p_item part)
    entity_field = getattr(entity, filter_request.field)

    # TODO: node split on . to get the nested field, for now top level

    # sqlalchemy.sql.elements.BinaryExpression
    expression = entity_field[filter_request.node]

    # TODO: cast statement to cast the value to the correct type
    # when value is a list it can either be a list of strings (astext) or a list of ints (Numeric)
    # when value is a string it can either be json (statement can just be returned) or a string (astext)
    # when value is a number it is a number

    # TODO: what is the operator

    query = query.filter(
        expression.op(filter_request.operator)(filter_request.value)
    )

    return query
