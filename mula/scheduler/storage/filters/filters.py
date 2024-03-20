from typing import Literal

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
    field: str | None = None
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
    value: str | int | float | bool | None | list[str] | list[int] | list[float] | list[bool] | list[None]


class FilterRequest(BaseModel):
    """Represents a filter request.

    Args:
        filters: The filter criteria, which can be a list of Filter objects or
        a dictionary of lists.
    """

    filters: list["Filter"] | dict[str, list["Filter"]]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if isinstance(self.filters, list):
            self.filters = {"and": self.filters}
