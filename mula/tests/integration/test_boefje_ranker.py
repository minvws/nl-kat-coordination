import unittest
import uuid
from datetime import datetime, timezone
from unittest import mock

import mmh3
from scheduler import config, models, rankers

from tests import factories


class BoefjeRankerTestCase(unittest.TestCase):
    def setUp(self):
        cfg = config.settings.Settings()

        self.mock_ctx = mock.patch("scheduler.context.AppContext").start()
        self.mock_ctx.config = cfg

        self.mock_get_tasks_by_hash = mock.patch(
            "scheduler.context.AppContext.task_store.get_tasks_by_hash",
        ).start()

        self.mock_get_children_by_ooi = mock.patch(
            "scheduler.context.AppContext.services.octopoes.get_children_by_ooi",
        ).start()

        self.mock_get_findings_by_ooi = mock.patch(
            "scheduler.context.AppContext.services.octopoes.get_findings_by_ooi",
        ).start()

        self.ranker = rankers.BoefjeRanker(self.mock_ctx)

    def test_rank(self):
        # Arrange
        scan_profile = factories.ScanProfileFactory(level=0)
        ooi = factories.OOIFactory(scan_profile=scan_profile)
        boefje = factories.PluginFactory(scan_level=0, consumes=[ooi.object_type])
        models.BoefjeTask(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        scheduler_id = uuid.uuid4()
        prior_tasks = []
        for i in range(10):
            task = models.Task(
                id=uuid.uuid4(),
                scheduler_id=scheduler_id,
                type="boefje",
                p_item=models.PrioritizedItem(
                    scheduler_id=scheduler_id,
                    hash=mmh3.hash_bytes(f"hash-{i}"),
                    priority=1,
                    data={},
                ),
                status=models.TaskStatus.QUEUED,
                created_at=datetime.now(timezone.utc),
                modified_at=datetime.now(timezone.utc),
            )
            prior_tasks.append(task)

        # Mock
        self.mock_get_tasks_by_hash.return_value = prior_tasks
        self.mock_get_children_by_ooi.return_value = []
        self.mock_get_findings_by_ooi.return_value = []
