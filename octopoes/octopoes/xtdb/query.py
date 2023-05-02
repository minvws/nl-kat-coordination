from dataclasses import dataclass, field
from typing import List, Optional, Type, Union

from octopoes.models import OOI
from octopoes.models.path import Direction, Path
from octopoes.models.types import get_abstract_types, get_relations


class InvalidField(ValueError):
    pass


class InvalidPath(ValueError):
    pass


@dataclass
class Query:
    """Object representing an XTDB query.

        result_type: The OOI Type being queried: executing the query should yield only this OOI Type.

    Example usage:

    >>> query = Query(Network).where(Network, name="test")
    >>> query = query.where(Finding, ooi=Network)
    >>> query.format()
    '
    {:query {:find [(pull Network [*])] :where [
        [ Network :Network/name "test" ]
        [ Finding :Finding/ooi Network ]
    ]}}
    '
    """

    result_type: Type[OOI]

    _where_clauses: List[str] = field(default_factory=list)
    _limit: Optional[int] = None
    _offset: Optional[int] = None

    def where(self, ooi_type: Type[OOI], **kwargs) -> "Query":
        for field_name, value in kwargs.items():
            self._where_field_is(ooi_type, field_name, value)

        return self

    def format(self) -> str:
        return "\n" + self._compile(separator="\n    ") + "\n"

    @classmethod
    def from_path(cls, path: Path) -> "Query":
        """
        Create a query from a Path.

        The last segment in the path is assumed to be the queries OOI Type. You can change this by calling the
        query() method after initialization for the required target OOI Type.
        """

        ooi_type = path.segments[-1].target_type
        query = Query(ooi_type)

        for segment in path.segments:
            if segment.direction is Direction.OUTGOING:
                query = query.where(segment.source_type, **{segment.property_name: segment.target_type})
                continue

            query = query.where(segment.target_type, **{segment.property_name: segment.source_type})

        return query

    def query(self, ooi_type: Type[OOI]) -> "Query":
        """Change the target object type of the Query after initialization, e.g. when using from_relation_path()"""

        self.result_type = ooi_type

        return self

    def limit(self, limit: int) -> "Query":
        self._limit = limit

        return self

    def offset(self, offset: int) -> "Query":
        self._offset = offset

        return self

    def _where_field_is(self, ooi_type: Type[OOI], field_name: str, value: Union[Type[OOI], str]) -> None:
        abstract_types = get_abstract_types()

        if field_name not in ooi_type.__fields__:
            raise InvalidField(f'"{field_name}" is not a field of {ooi_type.get_object_type()}')

        if isinstance(value, str):
            value = value.replace('"', r"\"")
            self._add_where_statement(ooi_type, field_name, f'"{value}"')
            return

        if not isinstance(value, type):
            raise InvalidField(f"value '{value}' should be a string or an OOI Type")

        if not issubclass(value, OOI):
            raise InvalidField(f"{value} is not an OOI")

        if field_name not in get_relations(ooi_type):
            raise InvalidField(f'"{field_name}" is not a relation of {ooi_type.get_object_type()}')

        if ooi_type in abstract_types:
            self._add_or_statement(ooi_type, field_name, value.get_object_type())
            return

        self._assert_type(value)
        self._add_where_statement(ooi_type, field_name, value.get_object_type())

    def _add_where_statement(self, ooi_type: Type[OOI], field_name: str, to_alias: str) -> None:
        from_alias = ooi_type.get_object_type()
        self._where_clauses.append(self._assert_type(ooi_type))

        self._where_clauses.append(self._relationship(from_alias, from_alias, field_name, to_alias))

    def _add_or_statement(self, ooi_type: Type[OOI], field_name: str, to_alias: str) -> None:
        self._where_clauses.append(self._assert_type(ooi_type))

        self._where_clauses.append(
            self._or_statement(
                ooi_type.get_object_type(),
                ooi_type.__subclasses__(),
                field_name,
                to_alias,
            )
        )

    def _or_statement(self, from_alias: str, concrete_types: List[Type[OOI]], field_name: str, to_alias: str) -> str:
        relationships = [
            self._relationship(from_alias, concrete_type.get_object_type(), field_name, to_alias)
            for concrete_type in concrete_types
        ]

        return f"(or {' '.join(relationships)} )"

    def _relationship(self, from_alias: str, field_type: str, field_name: str, to_alias: str) -> str:
        return f"[ {from_alias} :{field_type}/{field_name} {to_alias} ]"

    def _assert_type(self, object_type: Type[OOI]) -> str:
        return f"[ {object_type.get_object_type()} :object_type \"{object_type.get_object_type()}\" ]"

    def _compile_where_clauses(self, *, separator=" ") -> str:
        return separator + separator.join(sorted(set(self._where_clauses)))

    def _compile(self, *, separator=" ") -> str:
        self._where_clauses.append(self._assert_type(self.result_type))
        where_clauses = self._compile_where_clauses(separator=separator)
        compiled = f"{{:query {{:find [(pull {self.result_type.get_object_type()} [*])] :where [{where_clauses}]"

        if self._limit is not None:
            compiled += f" :limit {self._limit}"

        if self._offset is not None:
            compiled += f" :offset {self._offset}"

        return compiled + "}}"

    def __str__(self) -> str:
        return self._compile()

    def __eq__(self, other: "Query"):
        return str(self) == str(other)
