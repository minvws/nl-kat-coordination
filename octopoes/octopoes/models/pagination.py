from typing import Generic, List, TypeVar

from pydantic.generics import GenericModel

T = TypeVar("T")


class Paginated(GenericModel, Generic[T]):
    count: int
    items: List[T]
