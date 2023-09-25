from sqlalchemy.orm.query import Query
from sqlalchemy.sql.elements import BinaryExpression

from .casting import cast_expression
from .comparison import Comparator
from .filters import FilterRequest
from .operators import FILTER_OPERATORS


def apply_filter(entity, query: Query, filter_request: FilterRequest):
    """Apply the filter criteria to a SQLAlchemy query.

    Args:
        entity: The SQLAlchemy entity to apply the filter to.
        query: The SQLAlchemy query to apply the filter to.
        filter_request: The FilterRequest containing the filter criteria.

    Returns:
        A filtered SQLAlchemy query.
    """
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

            # If a nested field is being selected we need to traverse the nested
            # fields and return the correct expression.
            if len(filter_field.split("__")) > 1:
                for nested_field in filter_field.split("__"):
                    entity_attr = entity_attr[nested_field]

            # If the filter field is the same as the column name, return the
            # expression as is.
            else:
                entity_attr = entity_attr if filter_field == filter_.column else entity_attr[filter_field]

            # Cast the expression to the correct type based on the filter value
            if isinstance(entity_attr, BinaryExpression):
                entity_attr = cast_expression(entity_attr, filter_)

            # Based on the operator in the filter request we apply the correct
            # comparator function to the expression.
            expression = Comparator(filter_.operator).compare(entity_attr, filter_.value)
            expressions.append(expression)

        # Apply the filter operation to the query
        query = query.filter(FILTER_OPERATORS[operator](*expressions))  # type: ignore

    return query
