import uuid
from typing import Any, ClassVar

import mmh3
import pydantic
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Query

from scheduler import models


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

    @property
    def hash(self) -> str:
        return mmh3.hash_bytes(f"{self.id}-{self.name}").hex()


def create_test_model() -> TestModel:
    return TestModel(
        id=uuid.uuid4().hex,
        name=uuid.uuid4().hex,
    )


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


def create_p_item(scheduler_id: str, priority: int, task: models.Task | None = None) -> models.PrioritizedItem:
    if task is None:
        task = create_task()

    return models.PrioritizedItem(
        scheduler_id=scheduler_id,
        priority=priority,
        task_id=task.id,
        task=task,
    )


def create_task() -> models.Task:
    return models.Task(
        hash=uuid.uuid4().hex,
        data=TestModel(
            id=uuid.uuid4().hex,
            name=uuid.uuid4().hex,
        ).model_dump(),
    )


def create_run(p_item: models.PrioritizedItem) -> models.TaskRun:
    return models.TaskRun(
        id=p_item.id,
        hash=p_item.hash,
        type=TestModel.type,
        scheduler_id=p_item.scheduler_id,
        p_item=p_item,
        status=models.TaskStatus.QUEUED,
    )


def compile_query(query: Query) -> str:
    return str(query.statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
