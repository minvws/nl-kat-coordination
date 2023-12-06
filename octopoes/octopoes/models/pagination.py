from typing import Generic, List, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Paginated(BaseModel, Generic[T]):
    count: int
    items: List[T]
