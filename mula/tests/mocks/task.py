import uuid
from typing import ClassVar

import pydantic


class MockTask(pydantic.BaseModel):
    type: ClassVar[str] = "mock-task"

    id: str = pydantic.Field(default_factory=lambda: uuid.uuid4().hex)

    def hash(self):
        return self.id
