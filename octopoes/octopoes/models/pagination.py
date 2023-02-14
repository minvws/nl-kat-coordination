from typing import Generic, TypeVar, List

from pydantic.generics import GenericModel


T = TypeVar("T")


class Paginated(GenericModel, Generic[T]):
    count: int
    items: List[T]
