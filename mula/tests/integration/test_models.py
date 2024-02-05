import unittest
import uuid
from datetime import datetime, timezone

from scheduler import models
from tests.utils import functions


class TaskTestCase(unittest.TestCase):
    def setUp(self):
        pass

    def test_task_update_status(self):
        scheduler_id = uuid.uuid4().hex

        p_item = functions.create_p_item(
            scheduler_id=scheduler_id,
            priority=1,
        )

        task = models.Task(
            id=p_item.id,
            scheduler_id=scheduler_id,
            type="test",
            p_item=p_item,
            status=models.TaskStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            modified_at=datetime.now(timezone.utc),
        )

        task.update_status(models.TaskStatus.QUEUED)

        self.assertIsNotNone(task.pending)

        breakpoint()
