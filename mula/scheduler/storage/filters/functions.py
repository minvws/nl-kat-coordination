import sqlalchemy
from sqlalchemy.orm import RelationshipProperty
from sqlalchemy.orm.query import Query
from sqlalchemy.sql.elements import BinaryExpression

from .casting import cast_expression
from .comparison import Comparator
from .errors import FilterError, MismatchedTypeError, UnsupportedTypeError
from .filters import FilterRequest
from .operators import FILTER_OPERATORS


def apply_filter(entity, query: Query, filter_request: FilterRequest) -> Query:
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
            if not hasattr(entity, filter_.column):
                raise FilterError(f"Invalid filter field: {filter_.column} (error: not found)")

            # If the filter field is not specified we will use the column name
            # as the filter_field
            filter_field = filter_.field if filter_.field else filter_.column

            # Return the selected attribute of the model, e.g. Model.selected_attr
            entity_attr = getattr(entity, filter_.column)

            # Check if the column we are filtering on is a relationship, if so
            # we need to join the related entity to the query.
            if hasattr(entity_attr, "property") and isinstance(entity_attr.property, RelationshipProperty):
                related_entity = entity_attr.property.mapper.class_
                query = query.join(related_entity)

            # If a nested field is being selected we need to traverse the nested
            # fields and return the correct expression.
            #
            # When selecting a nested field sqlalchemy uses index operators,
            # e.g. Model.selected_attr["nested_field"] this will return a
            # sqlalchemy.sql.elements.BinaryExpression whose type defaults to
            # JSON.
            if len(filter_field.split("__")) > 1:
                for nested_field in filter_field.split("__"):
                    if hasattr(entity_attr, "property") and isinstance(entity_attr.property, RelationshipProperty):
                        entity_attr = getattr(entity_attr.property.mapper.class_, nested_field)
                    else:
                        entity_attr = entity_attr[nested_field]
            else:
                if hasattr(entity_attr, "property") and isinstance(entity_attr.property, RelationshipProperty):
                    entity_attr = getattr(entity_attr.property.mapper.class_, filter_field)
                elif filter_field != filter_.column:
                    entity_attr = entity_attr[filter_field]

            # Cast the expression to the correct type based on the filter value
            if isinstance(entity_attr, BinaryExpression):
                try:
                    entity_attr = cast_expression(entity_attr, filter_)
                except (UnsupportedTypeError, MismatchedTypeError) as exc:
                    raise FilterError(f"Invalid filter value: {filter_.value} (error: {exc})")

            # Based on the operator in the filter request we apply the correct
            # comparator function to the expression.
            try:
                expression = Comparator(filter_.operator).compare(entity_attr, filter_.value)
            except sqlalchemy.exc.ArgumentError as exc:
                raise FilterError(f"Invalid filter value: {filter_.value} (sql error: {exc})")

            expressions.append(expression)

        # Apply the filter operation to the query
        query = query.filter(FILTER_OPERATORS[operator](*expressions))

    return query
