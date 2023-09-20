import json
from typing import Dict, List, Literal, Optional, Union

from pydantic import BaseModel
from sqlalchemy import Boolean, Numeric, and_, not_, or_
from sqlalchemy.orm.query import Query
from sqlalchemy.sql.elements import BinaryExpression


class UnsupportedTypeError(Exception):
    pass


class MismatchedTypeError(Exception):
    pass


# Define supported filter operators
FILTER_OPERATORS = {
    "and": and_,
    "or": or_,
    "not": not_,
}


class Comparator:

    # Comparision operators and their corresponding functions
    OPERATORS = {
        "==": lambda x, y: x == y,
        "eq": lambda x, y: x == y,

        "!=": lambda x, y: x != y,
        "ne": lambda x, y: x != y,

        "is": lambda x, y: x.is_(y),
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
        "match": lambda x, y: x.match(y),
        "starts_with": lambda x, y: x.startswith(y),

        # Contains; returns true if the left hand side value contains all the
        # elements of the right hand side
        "@>": lambda x, y: x.op('@>')(y),

        # Contained by; returns true if the right hand side value contains all
        # the elements of the left hand side
        "<@": lambda x, y: x.op('<@')(y),

        # Contains key; returns true if the JSON object contains the specified
        # key
        "@?": lambda x, y: x.op('@?')(y),

        # Matches query; used by full text search in combination with tsquery
        # and tsvector data types
        "@@": lambda x, y: x.op('@@')(y),
    }

    def __init__(self, operator: str):
        if operator not in self.OPERATORS:
            raise ValueError(f"Operator {operator} not supported")

        self.operator = operator
        self.operator_func = self.OPERATORS.get(operator)

    def compare(self, x, y):
        return self.operator_func(x, y)

class Filter(BaseModel):
    column: str
    field: Optional[str]
    operator: Literal["==", "eq", "is", "!=", "ne", "is_not", "is_null", "is_not_null", ">", "gt", "<", "lt", ">=", "gte", "<=", "lte", "like", "not_like", "ilike", "not_ilike", "in", "not_in", "contains", "any", "match", "starts_with", "@>", "<@", "@?", "@@"]
    value: Union[str, int, float, bool, None, List[str], List[int], List[float], List[bool], List[None]]


class FilterRequest(BaseModel):
    """Represents a filter request.
    """

    filters: Union[List["Filter"], Dict[str, List["Filter"]]]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if isinstance(self.filters, list):
            expressions: List[Filter] = []
            for expression in self.filters:
                expressions.append(expression)

            self.filters = {"and": expressions}

def _cast_expression(expression: BinaryExpression, filter_: Filter) -> BinaryExpression:
    """ Cast the JSON value to the correct type, we do that by looking at the
    type of the value in the filter request:

    * When value is a list it can either be a list of strings (astext)
      or a list of ints (Numeric)

    * When value is a string it can either be json (statement can just be
      returned) or a string (astext)

    * When value is a number it is a numeric value (Numeric)
    """
    value_type = type(filter_.value)
    if value_type == list:
        if len(filter_.value) == 0:
            raise UnsupportedTypeError("Empty list not supported")

        for v in filter_.value:
            if type(v) != type(filter_.value[0]):
                raise MismatchedTypeError("List values must be of the same type")

        element_type = type(filter_.value[0])
        if element_type == str:
            expression = expression.astext
        elif element_type in [int, float]:
            expression = expression.cast(Numeric)
        elif element_type in [bool, None]:
            expression = expression.cast(Boolean)
        else:
            raise UnsupportedTypeError(f"Unsupported type {element_type}")
    elif value_type == str:
        # Check if value is a json object, or just a string. so we need to
        # check if the value can be decoded. If it can't be decoded, we assume
        # it is a string and cast it to text. NOTE: "123" is a valid json
        # object, so we need to check if the value is a dict after decoding
        # it. If it is a dict, we assume it is a json object and return the
        # expression as is. If it is not a dict, we assume it is a string and
        # cast it to text.
        try:
            decoded_value = json.loads(filter_.value)
            if isinstance(decoded_value, dict):
                return expression
            expression = expression.astext
        except json.JSONDecodeError:
            expression = expression.astext
    elif value_type in [int, float]:
        expression = expression.cast(Numeric)
    else:
        raise UnsupportedTypeError(f"Unsupported type {value_type}")

    return expression


def apply_filter(entity, query: Query, filter_request: FilterRequest):
    if not isinstance(filter_request.filters, dict):
        raise ValueError("Filter request must be a dict")

    for operator in filter_request.filters:
        expressions = []
        for filter_ in filter_request.filters[operator]:
            filter_field = filter_.field if filter_.field else filter_.column

            # Return the selected attribute of the model, e.g. Model.selected_attr
            entity_attr = getattr(entity, filter_.column)

            # When selecting a nested field sqlalchemy uses index operators,
            # e.g. Model.selected_attr["nested_field"] this will return a
            # sqlalchemy.sql.elements.BinaryExpression whose type defaults to
            # JSON.
            #
            # If a nested field is being selected we need to traverse the nested
            # fields and return the correct expression.
            if len(filter_field.split("__")) == 1:
                expression = entity_attr if filter_field == filter_.column else entity_attr[filter_field]
            else:
                expression = entity_attr
                for f in filter_field.split("__"):
                    expression = expression[f]

            if isinstance(expression, BinaryExpression):
                expression = _cast_expression(expression, filter_)

            # Based on the operator in the filter request we apply the correct
            # comparator function to the expression.
            expression = Comparator(filter_.operator).compare(expression, filter_.value)
            expressions.append(expression)

        # Apply the filter operation to the query
        query = query.filter(
            FILTER_OPERATORS[operator](*expressions)  # type: ignore
        )

    return query
