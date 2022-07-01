from __future__ import annotations

from enum import Enum
from typing import Type, List, Set, Optional, Tuple

from pyparsing import Word, alphas, ParseException

from octopoes.models import OOI
from octopoes.models.types import type_by_name, get_relation, get_concrete_types, to_concrete, get_relations

incoming_step_grammar = "<" + Word(alphas + "_") + "[" + "is" + Word(alphas) + "]"


class Direction(Enum):
    OUTGOING = 0
    INCOMING = 1


class Segment:
    def __init__(
        self,
        source_type: Type[OOI],
        direction: Direction,
        property_name: str,
        target_type: Type[OOI],
    ):
        self.source_type = source_type
        self.direction = direction
        self.property_name = property_name
        self.target_type = target_type

    @classmethod
    def parse_step(cls, step: str) -> Tuple[Direction, str, Optional[Type[OOI]]]:
        try:
            parsed_step = incoming_step_grammar.parse_string(step)
            incoming, property_name, _, _, target_type, _ = parsed_step
            return Direction.INCOMING, property_name, type_by_name(target_type)
        except ParseException:
            return Direction.OUTGOING, step, None

    @classmethod
    def calculate_step(cls, source_type: Type[OOI], step: str):
        direction, property_name, explicit_target_type = cls.parse_step(step)
        target_type = explicit_target_type if explicit_target_type else get_relation(source_type, property_name)
        return cls(source_type, direction, property_name, target_type)

    def reverse(self) -> Segment:
        return self.__class__(
            self.target_type,
            Direction.OUTGOING if self.direction == Direction.INCOMING else Direction.INCOMING,
            self.property_name,
            self.source_type,
        )

    def __eq__(self, other: Segment) -> bool:
        return (
            self.source_type == other.source_type
            and self.direction == other.direction
            and self.property_name == other.property_name
        )

    def __str__(self):
        if self.direction == Direction.INCOMING:
            return f"<{self.property_name}[is {self.target_type.get_object_type()}]"
        else:
            return f"{self.property_name}"

    def __repr__(self):
        return str(self)


class Path:
    def __init__(self, segments: List[Segment]):
        self.segments = segments

    @classmethod
    def parse(cls, path: str):
        start_type, step, *rest = path.split(".")

        segments = [Segment.calculate_step(type_by_name(start_type), step)]
        for next_step in rest:
            segments.append(Segment.calculate_step(segments[-1].target_type, next_step))

        return Path(segments)

    def reverse(self) -> Path:
        return Path([segment.reverse() for segment in reversed(self.segments)])

    def __str__(self) -> str:
        start_type = self.segments[0].source_type.get_object_type()
        segments = ".".join(map(str, self.segments))
        return f"{start_type}.{segments}"

    def __eq__(self, other: Path):
        return str(self) == str(other)

    def __lt__(self, other):
        return str(self) < str(other)

    def __hash__(self):
        return hash(str(self))


def get_paths_to_neighours(source_type: Type[OOI]) -> Set[Path]:
    relation_paths = set()
    for property_name, related_type in get_relations(source_type).items():
        relation_paths.add(Path([Segment(source_type, Direction.OUTGOING, property_name, related_type)]))

    for other_type in get_concrete_types():
        for property_name, related_type in get_relations(other_type).items():
            if source_type in to_concrete({related_type}):
                relation_paths.add(Path([Segment(source_type, Direction.INCOMING, property_name, other_type)]))

    return relation_paths


def get_max_scan_level_inheritance(segment: Segment) -> int:
    if segment.direction == Direction.INCOMING:
        return segment.target_type.__fields__[segment.property_name].field_info.extra.get("max_issue_scan_level", None)
    else:
        return segment.source_type.__fields__[segment.property_name].field_info.extra.get(
            "max_inherit_scan_level", None
        )


def get_max_scan_level_issuance(segment: Segment) -> int:
    if segment.direction == Direction.INCOMING:
        return segment.target_type.__fields__[segment.property_name].field_info.extra.get(
            "max_inherit_scan_level", None
        )
    else:
        return segment.source_type.__fields__[segment.property_name].field_info.extra.get("max_issue_scan_level", None)
