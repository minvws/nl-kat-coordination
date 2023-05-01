from dataclasses import dataclass, field
from typing import List, Type, Union

from octopoes.models import OOI
from octopoes.models.types import get_abstract_types, get_relation, get_relations


class InvalidField(ValueError):
    pass


class InvalidPath(ValueError):
    pass


@dataclass
class Query:
    """
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

    result_ooi_type: Type[OOI]

    _where_clauses: List[str] = field(default_factory=list)

    def where(self, ooi_type: Type[OOI], **kwargs) -> "Query":
        for field_name, value in kwargs.items():
            self._where_field_is(ooi_type, field_name, value)

        return self

    def format(self) -> str:
        return "\n" + self._compile(separator="\n    ") + "\n"

    @classmethod
    def from_relation_path(cls, ooi_type: Type[OOI], path: str) -> "Query":
        query = Query(ooi_type)

        for field_name in path.split("."):
            try:
                relation = get_relation(ooi_type, field_name)
                query = query.where(ooi_type, **{field_name: relation})
            except (InvalidField, KeyError) as e:
                raise InvalidPath("Not a valid relation path") from e

            ooi_type = relation

        return query

    def query(self, ooi_type: Type[OOI]) -> "Query":
        self.result_ooi_type = ooi_type
        return self

    def _where_field_is(self, ooi_type: Type[OOI], field_name: str, value: Union[Type[OOI], str]) -> None:
        abstract_types = get_abstract_types()

        if field_name not in ooi_type.__fields__:
            raise InvalidField(f'"{field_name}" is not a field of {ooi_type.get_object_type()}')

        if isinstance(value, str):
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

        self._add_where_statement(ooi_type, field_name, value.get_object_type())

    def _add_where_statement(self, ooi_type: Type[OOI], field_name: str, to_alias: str) -> None:
        from_alias = ooi_type.get_object_type()

        self._where_clauses.append(self._relationship(from_alias, from_alias, field_name, to_alias))

    def _add_or_statement(self, ooi_type: Type[OOI], field_name: str, to_alias: str) -> None:
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

    def _compile_where_clauses(self, *, separator=" ") -> str:
        return separator + separator.join(self._where_clauses)

    def _compile(self, *, separator=" ") -> str:
        where_clauses = self._compile_where_clauses(separator=separator)

        return f"{{:query {{:find [(pull {self.result_ooi_type.get_object_type()} [*])] :where [{where_clauses}]}}}}"

    def __str__(self) -> str:
        return self._compile()
