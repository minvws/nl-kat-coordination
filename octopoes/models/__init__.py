from __future__ import annotations

import abc
from enum import Enum
from typing import (
    List,
    TypeVar,
    Literal,
    Dict,
    Any,
    Optional,
    Type,
    Set,
    Union,
    Tuple,
)

from pydantic import BaseModel, Field, conint
from typing_extensions import Annotated


class ScanProfileBase(BaseModel, abc.ABC):
    reference: Reference
    level: conint(ge=0, le=4)

    def __eq__(self, other):
        if isinstance(other, ScanProfileBase) and self.__class__ == other.__class__:
            return self.reference == other.reference and self.level == other.level
        return False

    @property
    def human_readable(self) -> str:
        return f"L{self.level}"


class EmptyScanProfile(ScanProfileBase):
    scan_profile_type: Literal["empty"] = "empty"
    level: conint(ge=0, le=0) = 0


class DeclaredScanProfile(ScanProfileBase):
    scan_profile_type: Literal["declared"] = "declared"
    level: conint(ge=0, le=4)


class Inheritance(BaseModel):
    parent: Reference
    source: Reference
    level: conint(ge=0, le=4)
    depth: int

    @property
    def human_readable(self) -> str:
        return f"L{self.level}"


class InheritedScanProfile(ScanProfileBase):
    scan_profile_type: Literal["inherited"] = "inherited"
    inheritances: List[Inheritance] = Field(default_factory=list)

    def __eq__(self, other):
        return super().__eq__(other) and self.inheritances == other.inheritances


ScanProfile = Annotated[
    Union[EmptyScanProfile, InheritedScanProfile, DeclaredScanProfile], Field(discriminator="scan_profile_type")
]


class OOI(BaseModel, abc.ABC):
    object_type: Literal["OOI"]

    scan_profile: Optional[ScanProfile]

    _natural_key_attrs: List[str] = []
    _reverse_relation_names: Dict[str, str] = {}
    _information_value: List[str] = []
    _traversable = True

    primary_key: str = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.primary_key = f"{self.get_object_type()}|{self.natural_key}"

    def __str__(self):
        return self.primary_key

    @classmethod
    def get_object_type(cls) -> str:
        return cls.__name__

    # FIXME: Legacy usage in Rocky/Boefjes
    @classmethod
    def get_ooi_type(cls) -> str:
        return cls.get_object_type()

    # FIXME: Legacy usage in Rocky/Boefjes
    @property
    def ooi_type(self) -> str:
        return self.get_object_type()

    @property
    def human_readable(self) -> str:
        return self.format_reference_human_readable(self.reference)

    @property
    def natural_key(self) -> str:
        parts = []

        for attr in self._natural_key_attrs:
            part = getattr(self, attr)
            if part is None:
                part = ""
            if isinstance(part, Reference):
                part = part.natural_key
            elif isinstance(part, Enum):
                part = str(part.value)
            else:
                part = str(part)

            parts.append(part)

        return "|".join(parts)

    def get_information_id(self) -> str:
        def format_attr(value_: Any) -> str:
            if isinstance(value_, Enum):
                return value_.value
            return value_

        parts = [self.__class__.__name__]
        for attr in self._information_value:
            value = self.__getattribute__(attr)
            parts.append(format_attr(value))
        return "|".join(map(str, parts))

    @property
    def reference(self) -> Reference:
        return Reference(self.primary_key)

    @classmethod
    def get_reverse_relation_name(cls, attr: str) -> str:
        return cls._reverse_relation_names.get(attr, f"{cls.get_object_type()}_{attr}")

    @classmethod
    def get_tokenized_primary_key(cls, natural_key: str):
        token_tree = build_token_tree(cls)
        natural_key_parts = natural_key.split("|")

        def hydrate(node) -> Union[Dict, str]:
            for key, value in node.items():
                if isinstance(value, dict):
                    node[key] = hydrate(value)
                else:
                    node[key] = natural_key_parts.pop(0)
            return node

        return PrimaryKeyToken.parse_obj(hydrate(token_tree))

    @classmethod
    def format_reference_human_readable(cls, reference: Reference) -> str:
        return str(reference)

    @classmethod
    def traversable(cls) -> bool:
        return cls._traversable


OOIClassType = TypeVar("OOIClassType")


class Reference(str):
    def __new__(cls, *args, **kwargs):
        return str.__new__(cls, *args, **kwargs)

    @classmethod
    def parse(cls, ref_str: str) -> Tuple[str, str]:
        object_type, *natural_key_parts = ref_str.split("|")
        return object_type, "|".join(natural_key_parts)

    @property
    def class_(self) -> str:
        return self.parse(self)[0]

    @property
    def natural_key(self) -> str:
        return self.parse(self)[1]

    @property
    def class_type(self) -> Type[OOI]:
        from octopoes.models.types import type_by_name

        object_type, natural_key = self.parse(self)
        ooi_class = type_by_name(object_type)
        return ooi_class

    @property
    def tokenized(self) -> PrimaryKeyToken:
        return self.class_type.get_tokenized_primary_key(self.natural_key)

    @property
    def human_readable(self) -> str:
        return self.class_type.format_reference_human_readable(self)

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(
            examples=["Network|internet", "IPAddressV4|internet|1.1.1.1"],
        )

    @classmethod
    def validate(cls, v):
        if not isinstance(v, str):
            raise TypeError("string required")
        return cls(str(v))

    def __repr__(self):
        return f"Reference({super().__repr__()})"

    @classmethod
    def from_str(cls, ref_str: str) -> Reference:
        return cls(ref_str)


class PrimaryKeyToken(BaseModel):
    __root__: Dict[str, Union[str, PrimaryKeyToken]]

    def __getattr__(self, attr_name: str) -> Union[str, PrimaryKeyToken]:
        return self.__root__[attr_name]


PrimaryKeyToken.update_forward_refs()


def get_leaf_subclasses(cls: Type[OOI]) -> Set[Type[OOI]]:
    if not cls.__subclasses__():
        return {cls}
    child_sets = [get_leaf_subclasses(child_cls) for child_cls in cls.__subclasses__()]
    return set().union(*child_sets)


def build_token_tree(ooi_class: Type[OOI]) -> Dict:
    tokens = {}

    for attribute in ooi_class._natural_key_attrs:
        field = ooi_class.__fields__[attribute]
        value = ""

        if field.type_ == Reference:
            from octopoes.models.types import related_object_type

            related_class = related_object_type(field)
            trees = [build_token_tree(related_class) for related_class in get_leaf_subclasses(related_class)]

            # combine trees
            value = {key: value_ for tree in trees for key, value_ in tree.items()}

        tokens[attribute] = value
    return tokens


DeclaredScanProfile.update_forward_refs()
InheritedScanProfile.update_forward_refs()
Inheritance.update_forward_refs()
EmptyScanProfile.update_forward_refs()
