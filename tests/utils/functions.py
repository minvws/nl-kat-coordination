import datetime
import uuid
from typing import Dict

import pydantic
from scheduler import models


class TestModel(pydantic.BaseModel):
    id: str
    name: str


def create_p_item(scheduler_id: str, priority: int, data: TestModel = None) -> models.PrioritizedItem:
    if data is None:
        data = TestModel(
            id=uuid.uuid4().hex,
            name=uuid.uuid4().hex,
        )

    return models.PrioritizedItem(
        scheduler_id=scheduler_id,
        priority=priority,
        data=data,
    )


def create_task(p_item: models.PrioritizedItem) -> models.Task:
    return models.Task(
        id=p_item.id,
        hash=p_item.hash,
        scheduler_id=p_item.scheduler_id,
        p_item=p_item,
        status=models.TaskStatus.QUEUED,
        created_at=datetime.datetime.utcnow(),
        modified_at=datetime.datetime.utcnow(),
    )
