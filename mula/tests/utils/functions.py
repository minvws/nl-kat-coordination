import uuid
from typing import Any, ClassVar

import pydantic
from scheduler import models
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Query


class TestModel(pydantic.BaseModel):
    type: ClassVar[str] = "test-model"
    id: str
    name: str
    count: int = 0
    categories: list[str] = None
    child: Any = None

    def __init__(self, **data: Any):
        super().__init__(**data)

        if self.categories is None:
            self.categories = []


def create_p_item_request(priority: int, data: TestModel | None = None) -> models.PrioritizedItemRequest:
    if data is None:
        data = TestModel(
            id=uuid.uuid4().hex,
            name=uuid.uuid4().hex,
        )

    return models.PrioritizedItemRequest(
        priority=priority,
        data=data.model_dump(),
    )


def create_p_item(scheduler_id: str, priority: int, data: TestModel | None = None) -> models.PrioritizedItem:
    if data is None:
        data = TestModel(
            id=uuid.uuid4().hex,
            name=uuid.uuid4().hex,
        )

    return models.PrioritizedItem(
        scheduler_id=scheduler_id,
        priority=priority,
        data=data.model_dump(),
    )


def create_task(p_item: models.PrioritizedItem) -> models.Task:
    return models.Task(
        id=p_item.id,
        hash=p_item.hash,
        type=TestModel.type,
        scheduler_id=p_item.scheduler_id,
        p_item=p_item,
        status=models.TaskStatus.QUEUED,
    )


def compile_query(query: Query) -> str:
    return str(query.statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
