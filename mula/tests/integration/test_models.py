import unittest
import uuid
from datetime import datetime, timezone

from scheduler import models
from tests.utils import functions


class TaskTestCase(unittest.TestCase):
    def test_task_update_status_sequence(self):
        # Arrange
        p_item = functions.create_p_item(
            scheduler_id=uuid.uuid4().hex,
            priority=1,
        )

        task = models.Task(
            id=p_item.id,
            scheduler_id=p_item.scheduler_id,
            type="test",
            p_item=p_item,
            status=models.TaskStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            modified_at=datetime.now(timezone.utc),
        )

        # Act
        task.update_status(models.TaskStatus.QUEUED)
        task.update_status(models.TaskStatus.DISPATCHED)
        task.update_status(models.TaskStatus.RUNNING)
        task.update_status(models.TaskStatus.COMPLETED)

        # Assert
        self.assertIsNotNone(task.pending)
        self.assertIsNotNone(task.queued)
        self.assertIsNotNone(task.dispatched)
        self.assertIsNotNone(task.running)

    def test_task_update_status_non_consecutive(self):
        # Arrange
        p_item = functions.create_p_item(
            scheduler_id=uuid.uuid4().hex,
            priority=1,
        )

        task = models.Task(
            id=p_item.id,
            scheduler_id=p_item.scheduler_id,
            type="test",
            p_item=p_item,
            status=models.TaskStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            modified_at=datetime.now(timezone.utc),
        )

        # Act
        task.update_status(models.TaskStatus.DISPATCHED)

        # Assert
        self.assertIsNone(task.pending)
        self.assertIsNone(task.queued)
        self.assertIsNone(task.dispatched)
        self.assertIsNone(task.running)

    def test_task_update_status_equivalent(self):
        # Arrange
        p_item = functions.create_p_item(
            scheduler_id=uuid.uuid4().hex,
            priority=1,
        )

        task = models.Task(
            id=p_item.id,
            scheduler_id=p_item.scheduler_id,
            type="test",
            p_item=p_item,
            status=models.TaskStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            modified_at=datetime.now(timezone.utc),
        )

        # Act
        task.update_status(models.TaskStatus.PENDING)

        # Assert
        self.assertIsNone(task.pending)
        self.assertIsNone(task.queued)
        self.assertIsNone(task.dispatched)
        self.assertIsNone(task.running)

    def test_task_update_status_from_pending_to_queued(self):
        """When changing status from PENDING to QUEUED, the pending field
        should NOT be set to None."""
        # Arrange
        p_item = functions.create_p_item(
            scheduler_id=uuid.uuid4().hex,
            priority=1,
        )

        task = models.Task(
            id=p_item.id,
            scheduler_id=p_item.scheduler_id,
            type="test",
            p_item=p_item,
            status=models.TaskStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            modified_at=datetime.now(timezone.utc),
        )

        # Act
        task.update_status(models.TaskStatus.QUEUED)

        # Assert
        self.assertIsNotNone(task.pending)
        self.assertIsNone(task.queued)
        self.assertIsNone(task.dispatched)
        self.assertIsNone(task.running)

    def test_task_update_status_from_pending_to_cancelled(self):
        # Arrange
        p_item = functions.create_p_item(
            scheduler_id=uuid.uuid4().hex,
            priority=1,
        )

        task = models.Task(
            id=p_item.id,
            scheduler_id=p_item.scheduler_id,
            type="test",
            p_item=p_item,
            status=models.TaskStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            modified_at=datetime.now(timezone.utc),
        )

        # Act
        task.update_status(models.TaskStatus.CANCELLED)

        # Assert
        self.assertIsNotNone(task.pending)
        self.assertIsNone(task.queued)
        self.assertIsNone(task.dispatched)
        self.assertIsNone(task.running)

    def test_task_update_status_from_queued_to_dispatched(self):
        # Arrange
        p_item = functions.create_p_item(
            scheduler_id=uuid.uuid4().hex,
            priority=1,
        )

        task = models.Task(
            id=p_item.id,
            scheduler_id=p_item.scheduler_id,
            type="test",
            p_item=p_item,
            status=models.TaskStatus.QUEUED,
            created_at=datetime.now(timezone.utc),
            modified_at=datetime.now(timezone.utc),
        )

        # Act
        task.update_status(models.TaskStatus.DISPATCHED)

        # Assert
        self.assertIsNone(task.pending)
        self.assertIsNotNone(task.queued)
        self.assertIsNone(task.dispatched)
        self.assertIsNone(task.running)

    def test_task_update_status_from_queued_to_cancelled(self):
        # Arrange
        p_item = functions.create_p_item(
            scheduler_id=uuid.uuid4().hex,
            priority=1,
        )

        task = models.Task(
            id=p_item.id,
            scheduler_id=p_item.scheduler_id,
            type="test",
            p_item=p_item,
            status=models.TaskStatus.QUEUED,
            created_at=datetime.now(timezone.utc),
            modified_at=datetime.now(timezone.utc),
        )

        # Act
        task.update_status(models.TaskStatus.CANCELLED)

        # Assert
        self.assertIsNone(task.pending)
        self.assertIsNotNone(task.queued)
        self.assertIsNone(task.dispatched)
        self.assertIsNone(task.running)

    def test_task_update_status_from_dispatched_to_running(self):
        # Arrange
        p_item = functions.create_p_item(
            scheduler_id=uuid.uuid4().hex,
            priority=1,
        )

        task = models.Task(
            id=p_item.id,
            scheduler_id=p_item.scheduler_id,
            type="test",
            p_item=p_item,
            status=models.TaskStatus.DISPATCHED,
            created_at=datetime.now(timezone.utc),
            modified_at=datetime.now(timezone.utc),
        )

        # Act
        task.update_status(models.TaskStatus.RUNNING)

        # Assert
        self.assertIsNone(task.pending)
        self.assertIsNone(task.queued)
        self.assertIsNotNone(task.dispatched)
        self.assertIsNone(task.running)

    def test_task_update_status_from_dispatched_to_cancelled(self):
        # Arrange
        p_item = functions.create_p_item(
            scheduler_id=uuid.uuid4().hex,
            priority=1,
        )

        task = models.Task(
            id=p_item.id,
            scheduler_id=p_item.scheduler_id,
            type="test",
            p_item=p_item,
            status=models.TaskStatus.DISPATCHED,
            created_at=datetime.now(timezone.utc),
            modified_at=datetime.now(timezone.utc),
        )

        # Act
        task.update_status(models.TaskStatus.CANCELLED)

        # Assert
        self.assertIsNone(task.pending)
        self.assertIsNone(task.queued)
        self.assertIsNotNone(task.dispatched)
        self.assertIsNone(task.running)

    def test_task_update_status_from_running_to_completed(self):
        # Arrange
        p_item = functions.create_p_item(
            scheduler_id=uuid.uuid4().hex,
            priority=1,
        )

        task = models.Task(
            id=p_item.id,
            scheduler_id=p_item.scheduler_id,
            type="test",
            p_item=p_item,
            status=models.TaskStatus.RUNNING,
            created_at=datetime.now(timezone.utc),
            modified_at=datetime.now(timezone.utc),
        )

        # Act
        task.update_status(models.TaskStatus.COMPLETED)

        # Assert
        self.assertIsNone(task.pending)
        self.assertIsNone(task.queued)
        self.assertIsNone(task.dispatched)
        self.assertIsNotNone(task.running)

    def test_task_update_status_from_running_to_failed(self):
        # Arrange
        p_item = functions.create_p_item(
            scheduler_id=uuid.uuid4().hex,
            priority=1,
        )

        task = models.Task(
            id=p_item.id,
            scheduler_id=p_item.scheduler_id,
            type="test",
            p_item=p_item,
            status=models.TaskStatus.RUNNING,
            created_at=datetime.now(timezone.utc),
            modified_at=datetime.now(timezone.utc),
        )

        # Act
        task.update_status(models.TaskStatus.FAILED)

        # Assert
        self.assertIsNone(task.pending)
        self.assertIsNone(task.queued)
        self.assertIsNone(task.dispatched)
        self.assertIsNotNone(task.running)

    def test_task_update_status_from_running_to_cancelled(self):
        # Arrange
        p_item = functions.create_p_item(
            scheduler_id=uuid.uuid4().hex,
            priority=1,
        )

        task = models.Task(
            id=p_item.id,
            scheduler_id=p_item.scheduler_id,
            type="test",
            p_item=p_item,
            status=models.TaskStatus.RUNNING,
            created_at=datetime.now(timezone.utc),
            modified_at=datetime.now(timezone.utc),
        )

        # Act
        task.update_status(models.TaskStatus.CANCELLED)

        # Assert
        self.assertIsNone(task.pending)
        self.assertIsNone(task.queued)
        self.assertIsNone(task.dispatched)
        self.assertIsNotNone(task.running)
