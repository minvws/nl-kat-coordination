from typing import Dict, List, Literal, Optional, Union

from pydantic import BaseModel


class Filter(BaseModel):
    """Represents a filter condition.

    Attributes:
        column: The name of the column to filter on.
        field: An optional field name for nested filtering.
        operator: The comparison operator for the filter.
        value: The value to compare against.
    """

    column: str
    field: Optional[str] = None
    operator: Literal[
        "==",
        "eq",
        "!=",
        "ne",
        "is",
        "is_not",
        "is_null",
        "is_not_null",
        ">",
        "gt",
        "<",
        "lt",
        ">=",
        "gte",
        "<=",
        "lte",
        "like",
        "not_like",
        "ilike",
        "not_ilike",
        "in",
        "not_in",
        "contains",
        "any",
        "match",
        "starts_with",
        "@>",
        "<@",
        "@?",
        "@@",
    ]
    value: Union[str, int, float, bool, None, List[str], List[int], List[float], List[bool], List[None]]


class FilterRequest(BaseModel):
    """Represents a filter request.

    Args:
        filters: The filter criteria, which can be a list of Filter objects or
        a dictionary of lists.
    """

    filters: Union[List["Filter"], Dict[str, List["Filter"]]]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if isinstance(self.filters, list):
            expressions = []
            for expression in self.filters:
                expressions.append(expression)

            self.filters = {"and": expressions}
