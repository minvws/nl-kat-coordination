from typing import Any, ClassVar

import mmh3
import pydantic


class MockData(pydantic.BaseModel):
    type: ClassVar[str] = "test-model"
    id: str
    name: str
    count: int = 0
    categories: list[str] | None = None
    child: Any = None

    def __init__(self, **data: Any):
        super().__init__(**data)

        if self.categories is None:
            self.categories = []

    @property
    def hash(self) -> str:
        return mmh3.hash_bytes(f"{self.id}-{self.name}").hex()
