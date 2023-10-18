from dataclasses import dataclass, field
from typing import List, Optional, Set, Type, Union
from uuid import UUID, uuid4

from octopoes.models import OOI
from octopoes.models.path import Direction, Path
from octopoes.models.types import get_abstract_types, get_relations, to_concrete


class InvalidField(ValueError):
    pass


class InvalidPath(ValueError):
    pass


@dataclass
class Aliased:
    """OOI type wrapper to have control over the query alias used per type. This is necessary to traverse the same
    OOI type more than once, since by default we have that
        >>> Query(DNSAAAARecord)
        >>>     .where(DNSAAAARecord, hostname=Hostname)
        >>>     .where(Hostname, primary_key="Hostname|internet|test.com")
        >>>     .where(DNSNSRecord, hostname=Hostname)
        >>>     .where(DNSNSRecord, name_server_hostname=Hostname)
    needs the same Hostname to be both the DNSNSRecord.hostname and the DNSNSRecord.name_server_hostname.

    But if we use
        >>> hostname = A(Hostname)
        >>> Query(DNSAAAARecord)
        >>>     .where(DNSAAAARecord, hostname=hostname)
        >>>     .where(DNSNSRecord, name_server_hostname=hostname)
        >>>     .where(DNSNSRecord, hostname=Hostname)
        >>>     .where(Hostname, primary_key="Hostname|internet|test.com")
    we will get the DNSAAAARecords of the Hostname of the name server of "test.com".
    """

    type: Type[OOI]

    # The lambda makes it possible to mock the factory more easily, see:
    # https://stackoverflow.com/questions/61257658/python-dataclasses-mocking-the-default-factory-in-a-frozen-dataclass
    alias: UUID = field(default_factory=lambda: uuid4())


Ref = Union[Type[OOI], Aliased]
A = Aliased


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

    result_type: Ref

    _where_clauses: List[str] = field(default_factory=list)
    _find_clauses: List[str] = field(default_factory=list)
    _limit: Optional[int] = None
    _offset: Optional[int] = None

    def where(self, ooi_type: Ref, **kwargs) -> "Query":
        for field_name, value in kwargs.items():
            self._where_field_is(ooi_type, field_name, value)

        return self

    def format(self) -> str:
        return self._compile(separator="\n    ")

    @classmethod
    def from_path(cls, path: Path) -> "Query":
        """
        Create a query from a Path.

        The last segment in the path is assumed to be the queries OOI Type. Because paths often describe type traversal,
        we assume that every time we get a duplicate type, we have to alias it, except the target type.
        """

        ooi_type = path.segments[-1].target_type
        query = cls(ooi_type)
        alias_map = {}

        for segment in path.segments:
            source_ref = alias_map.get(segment.source_type.get_object_type(), segment.source_type)

            if segment.source_type.get_object_type() not in alias_map:  # Only happens on the first segment
                alias_map[segment.source_type.get_object_type()] = source_ref

            if segment.target_type.get_object_type() not in alias_map:
                target_ref = segment.target_type
                alias_map[target_ref.get_object_type()] = target_ref
            else:
                target_ref = A(segment.target_type)
                alias_map[segment.target_type.get_object_type()] = target_ref

            if segment.direction is Direction.OUTGOING:
                query = query.where(source_ref, **{segment.property_name: target_ref})
            else:
                query = query.where(target_ref, **{segment.property_name: source_ref})

        return query

    def count(self, ooi_type: Ref) -> "Query":
        self._find_clauses.append(f"(count {self._get_object_alias(ooi_type)})")

        return self

    def group_by(self, ooi_type: Ref) -> "Query":
        self._find_clauses.append(f"(pull {self._get_object_alias(ooi_type)} [*])")

        return self

    def limit(self, limit: int) -> "Query":
        self._limit = limit

        return self

    def offset(self, offset: int) -> "Query":
        self._offset = offset

        return self

    def _where_field_is(self, ref: Ref, field_name: str, value: Union[Ref, str, Set[str]]) -> None:
        ooi_type = ref.type if isinstance(ref, Aliased) else ref

        if field_name not in ooi_type.__fields__:
            raise InvalidField(f'"{field_name}" is not a field of {ooi_type.get_object_type()}')

        abstract_types = get_abstract_types()

        if ooi_type in abstract_types:
            if isinstance(value, str):
                value = value.replace('"', r"\"")
                self._add_or_statement(ref, field_name, f'"{value}"')
                return

            if not isinstance(value, type):
                raise InvalidField(f"value '{value}' for abstract class fields should be a string or an OOI Type")

            if issubclass(value, OOI):
                self._add_or_statement(
                    ref,
                    field_name,
                    self._get_object_alias(
                        value,
                    ),
                )
                return

        if isinstance(value, str):
            value = value.replace('"', r"\"")
            self._add_where_statement(ref, field_name, f'"{value}"')
            return

        if not isinstance(value, (type, Aliased)):
            raise InvalidField(f"value '{value}' should be a string or an OOI Type")

        if not isinstance(value, Aliased) and not issubclass(value, OOI):
            raise InvalidField(f"{value} is not an OOI")

        if field_name not in get_relations(ooi_type):
            raise InvalidField(f'"{field_name}" is not a relation of {ooi_type.get_object_type()}')

        self._add_where_statement(ref, field_name, self._get_object_alias(value))

    def _add_where_statement(self, ref: Ref, field_name: str, to_alias: str) -> None:
        ooi_type = ref.type if isinstance(ref, Aliased) else ref

        self._where_clauses.append(self._assert_type(ref, ooi_type))
        self._where_clauses.append(
            self._relationship(
                self._get_object_alias(ref),
                ooi_type.get_object_type(),
                field_name,
                to_alias,
            )
        )

    def _add_or_statement(self, ref: Ref, field_name: str, to_alias: str) -> None:
        ooi_type = ref.type if isinstance(ref, Aliased) else ref

        self._where_clauses.append(self._assert_type(ref, ooi_type))
        self._where_clauses.append(
            self._or_statement(
                self._get_object_alias(ref),
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

    def _assert_type(self, ref: Ref, ooi_type: Type[OOI]) -> str:
        if ooi_type not in get_abstract_types():
            return self._to_object_type_statement(ref, ooi_type)

        concrete = sorted(to_concrete({ooi_type}), key=lambda t: t.__name__)
        return f"(or {' '.join([self._to_object_type_statement(ref, x) for x in concrete])} )"

    def _to_object_type_statement(self, ref: Ref, other_type: Type[OOI]) -> str:
        return f'[ {self._get_object_alias(ref)} :object_type "{other_type.get_object_type()}" ]'

    def _compile_where_clauses(self, *, separator=" ") -> str:
        """Sorted and deduplicated where clauses, since they are both idempotent and commutative"""

        return separator + separator.join(sorted(set(self._where_clauses)))

    def _compile_find_clauses(self) -> str:
        return " ".join(self._find_clauses)

    def _compile(self, *, separator=" ") -> str:
        result_ooi_type = self.result_type.type if isinstance(self.result_type, Aliased) else self.result_type

        self._where_clauses.append(self._assert_type(self.result_type, result_ooi_type))
        where_clauses = self._compile_where_clauses(separator=separator)

        if not self._find_clauses:
            self._find_clauses = [f"(pull {self._get_object_alias(self.result_type)} [*])"]

        find_clauses = self._compile_find_clauses()
        compiled = f"{{:query {{:find [{find_clauses}] :where [{where_clauses}]"

        if self._limit is not None:
            compiled += f" :limit {self._limit}"

        if self._offset is not None:
            compiled += f" :offset {self._offset}"

        return compiled + "}}"

    def _get_object_alias(self, object_type: Ref) -> str:
        if isinstance(object_type, Aliased):
            return "?" + str(object_type.alias)

        return object_type.get_object_type()

    def __str__(self) -> str:
        return self._compile()

    def __eq__(self, other: "Query"):
        return str(self) == str(other)
