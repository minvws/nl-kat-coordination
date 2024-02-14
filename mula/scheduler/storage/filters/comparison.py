from sqlalchemy.sql.elements import BinaryExpression


class Comparator:
    # Comparison operators and their corresponding functions
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
        "@>": lambda x, y: x.op("@>")(y),
        # Contained by; returns true if the right hand side value contains all
        # the elements of the left hand side
        "<@": lambda x, y: x.op("<@")(y),
        # Contains key; returns true if the JSON object contains the specified
        # key
        "@?": lambda x, y: x.op("@?")(y),
        # Matches query; used by full text search in combination with tsquery
        # and tsvector data types
        "@@": lambda x, y: x.op("@@")(y),
    }

    def __init__(self, operator: str):
        """Initialise the Comparator class.

        Args:
            operator: The operator to use when comparing two values.
        """
        if operator not in self.OPERATORS:
            raise ValueError(f"Operator {operator} not supported")

        self.operator = operator
        self.operator_func = self.OPERATORS.get(operator, lambda x, y: x == y)

    def compare(
        self,
        x: BinaryExpression,
        y: str | int | float | bool | None | list[str] | list[int] | list[float] | list[bool] | list[None],
    ) -> BinaryExpression:
        """Compare two values using the operator specified in the constructor.

        Args:
            x: The left hand side value, e.g. the SQLAlchemy BinaryExpression.
            y: The right hand side value, e.g. the value to compare against.

        Returns:
            A SQLAlchemy BinaryExpression with the operator applied.
        """
        return self.operator_func(x, y)  # type: ignore
