from dataclasses import dataclass, field
from typing import List, Optional, Set, Type, Union

from octopoes.models import OOI
from octopoes.models.path import Direction, Path
from octopoes.models.types import get_abstract_types, get_relations, to_concrete


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
    _find_clauses: List[str] = field(default_factory=list)
    _limit: Optional[int] = None
    _offset: Optional[int] = None

    def where(self, ooi_type: Type[OOI], **kwargs) -> "Query":
        for field_name, value in kwargs.items():
            self._where_field_is(ooi_type, field_name, value)

        return self

    def format(self) -> str:
        return self._compile(separator="\n    ")

    @classmethod
    def from_path(cls, path: Path) -> "Query":
        """
        Create a query from a Path.

        The last segment in the path is assumed to be the queries OOI Type.
        """

        ooi_type = path.segments[-1].target_type
        query = cls(ooi_type)

        for segment in path.segments:
            if segment.direction is Direction.OUTGOING:
                query = query.where(segment.source_type, **{segment.property_name: segment.target_type})
            else:
                query = query.where(segment.target_type, **{segment.property_name: segment.source_type})

        return query

    def count(self, ooi_type: Type[OOI]) -> "Query":
        self._find_clauses.append(f"(count {ooi_type.get_object_type()})")

        return self

    def group_by(self, ooi_type: Type[OOI]) -> "Query":
        self._find_clauses.append(f"(pull {ooi_type.get_object_type()} [*])")

        return self

    def limit(self, limit: int) -> "Query":
        self._limit = limit

        return self

    def offset(self, offset: int) -> "Query":
        self._offset = offset

        return self

    def _where_field_is(self, ooi_type: Type[OOI], field_name: str, value: Union[Type[OOI], str, Set[str]]) -> None:
        if field_name not in ooi_type.__fields__:
            raise InvalidField(f'"{field_name}" is not a field of {ooi_type.get_object_type()}')

        abstract_types = get_abstract_types()

        if ooi_type in abstract_types:
            if isinstance(value, str):
                value = value.replace('"', r"\"")
                self._add_or_statement(ooi_type, field_name, f'"{value}"')
                return

            if not isinstance(value, type):
                raise InvalidField(f"value '{value}' for abstract class fields should be a string or an OOI Type")

            if issubclass(value, OOI):
                self._add_or_statement(ooi_type, field_name, value.get_object_type())
                return

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
                ooi_type.strict_subclasses(),
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

    def _assert_type(self, ooi_type: Type[OOI]) -> str:
        if ooi_type not in get_abstract_types():
            return self._to_object_type_statement(ooi_type, ooi_type)

        concrete = sorted(to_concrete({ooi_type}), key=lambda t: t.__name__)
        return f"(or {' '.join([self._to_object_type_statement(ooi_type, x) for x in concrete])} )"

    def _to_object_type_statement(self, ooi_type: Type[OOI], other_type: Type[OOI]) -> str:
        return f'[ {ooi_type.get_object_type()} :object_type "{other_type.get_object_type()}" ]'

    def _compile_where_clauses(self, *, separator=" ") -> str:
        """Sorted and deduplicated where clauses, since they are both idempotent and commutative"""

        return separator + separator.join(sorted(set(self._where_clauses)))

    def _compile_find_clauses(self) -> str:
        return " ".join(self._find_clauses)

    def _compile(self, *, separator=" ") -> str:
        self._where_clauses.append(self._assert_type(self.result_type))
        where_clauses = self._compile_where_clauses(separator=separator)

        if not self._find_clauses:
            self._find_clauses = [f"(pull {self.result_type.get_object_type()} [*])"]

        find_clauses = self._compile_find_clauses()
        compiled = f"{{:query {{:find [{find_clauses}] :where [{where_clauses}]"

        if self._limit is not None:
            compiled += f" :limit {self._limit}"

        if self._offset is not None:
            compiled += f" :offset {self._offset}"

        return compiled + "}}"

    def __str__(self) -> str:
        return self._compile()

    def __eq__(self, other: "Query"):
        return str(self) == str(other)
