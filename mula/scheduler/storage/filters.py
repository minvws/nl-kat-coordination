import json
from typing import Dict, List, Literal, Union

from pydantic import BaseModel
from sqlalchemy import Numeric, and_, not_, or_
from sqlalchemy.orm.query import Query

FILTER_OPERATORS = {
    "and": and_,
    "or": or_,
    "not": not_,
}


# TODO: check naming
class Comparator:
    OPERATORS = {
        "==": lambda x, y: x == y,
        "eq": lambda x, y: x == y,
        "is": lambda x, y: x.is_(y),

        "!=": lambda x, y: x != y,
        "ne": lambda x, y: x != y,
        "is_not": lambda x, y: x.isnot(y),

        "is_null": lambda x: x.is_(None),
        "is_not_null": lambda x: x.isnot(None),

        ">": lambda x, y: x > y,
        "gt": lambda x, y: x > y,

        "<": lambda x, y: x < y,
        "lt": lambda x, y: x < y,

        ">=": lambda x, y: x >= y,
        "gte": lambda x, y: x >= y,

        "<=": lambda x, y: x <= y,
        "lte": lambda x, y: x <= y,

        "like": lambda x, y: x.like(y),
        "not_like": lambda x, y: x.not_like(y),

        "ilike": lambda x, y: x.ilike(y),
        "not_ilike": lambda x, y: x.notilike(y),

        "in": lambda x, y: x.in_(y),
        "not_in": lambda x, y: x.not_in(y),

        "contains": lambda x, y: x.contains(y),
        "any": lambda x, y: x.any(y),

        "match": lambda x, y: x.match(y),
        "starts_with": lambda x, y: x.startswith(y),

        "@>": lambda x, y: x.op('@>')(y),
        "<@": lambda x, y: x.op('<@')(y),
        "@?": lambda x, y: x.op('@?')(y),
        "@@": lambda x, y: x.op('@@')(y),
    }

    def __init__(self, operator: str):
        if operator not in self.OPERATORS:
            raise ValueError(f"Operator {operator} not supported")

        self.operator = operator
        self.operator_func = self.OPERATORS.get(operator)

    def compare(self, x, y):
        return self.operator_func(x, y)


class FilterRequest(BaseModel):
    filters: Union[List["Filter"], Dict[str, List["Filter"]]]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if isinstance(self.filters, list):
            expressions: List[Filter] = []
            for expression in self.filters:
                expressions.append(expression)

            self.filters = {"and": expressions}

class Filter(BaseModel):
    column: str  # TODO: better descriptive naming
    field: str  # TODO: better descriptive naming
    operator: Literal["==", "eq", "is", "!=", "ne", "is_not", "is_null", "is_not_null", ">", "gt", "<", "lt", ">=", "gte", "<=", "lte", "like", "not_like", "ilike", "not_ilike", "in", "not_in", "contains", "any", "match", "starts_with", "@>", "<@", "@?", "@@"]
    value: str


# TODO: implement and, or, not
def apply_filter(entity, query: Query, filter_request: FilterRequest):
    if not isinstance(filter_request.filters, dict):
        raise ValueError("Filter request must be a dict")

    for operator in filter_request.filters:
        expressions = []
        for filter_ in filter_request.filters[operator]:
            # What is the json column to filter on?

            # Return the selected attribute of the model, e.g. Model.selected_attr
            entity_attr = getattr(entity, filter_.column)

            # When selecting a nested field sqlalchemy uses index operators, e.g.
            # Model.selected_attr["nested_field"] this will return a
            # sqlalchemy.sql.elements.BinaryExpression whose type defaults to JSON.
            #
            # If a nested field is being selected we need to traverse the nested
            # fields and return the correct expression.
            expression = entity_attr[filter_.field]
            if filter_.field.split("__") == 1:
                expression = entity_attr[filter_.field]
            else:
                expression = entity_attr
                for f in filter_.field.split("__"):
                    expression = expression[f]

            # TODO: boolean

            # Cast the JSON value to the correct type, we do that by looking at the
            # type of the value in the filter request:
            #
            # * when value is a list it can either be a list of strings (astext) or
            #   a list of ints (Numeric)
            # * when value is a string it can either be json (statement can just be
            #   returned) or a string (astext)
            # * when value is a number it is a number
            value_type = type(filter_.value)
            if value_type == list:
                if len(filter_.value) == 0:
                    pass  # TODO: in function return

                if isinstance(value_type, str):
                    expression = expression.astext
                elif type(filter_.value[0]) in [int, float]:
                    expression = expression.cast(Numeric)
                else:
                    raise Exception("Unsupported type")
            elif value_type == str:
                try:
                    json.loads(filter_.value)
                    # TODO: return statement in function
                except ValueError:
                    expression = expression.astext
            elif value_type in [int, float]:
                expression = expression.cast(Numeric)

            # Based on the operator in the filter request we apply the correct
            # comparator function to the expression.
            expression = Comparator(filter_.operator).compare(expression, filter_.value)
            expressions.append(expression)

        # Apply the filter operation to the query
        query = query.filter(
            FILTER_OPERATORS[operator](*expressions)  # type: ignore
        )

    return query
