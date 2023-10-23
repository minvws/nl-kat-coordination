import json
import random
import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import mmh3
from factory import fuzzy
from scheduler import config, models, rankers
from scheduler.connectors import services

from tests import factories


class BoefjeRankerTestCase(unittest.TestCase):
    def setUp(self):
        cfg = config.settings.Settings()

        self.mock_ctx = mock.patch("scheduler.context.AppContext").start()
        self.mock_ctx.config = cfg

        self.organisation = factories.OrganisationFactory()

        self.ranker = rankers.BoefjeRanker(self.mock_ctx)

        self.mock_get_tasks_by_hash = mock.patch(
            "scheduler.context.AppContext.datastores.task_store.get_tasks_by_hash",
        ).start()

        self.mock_get_objects_by_ooi = mock.patch(
            "scheduler.context.AppContext.services.octopoes.get_objects_by_ooi",
        ).start()

        self.mock_get_findings_by_ooi = mock.patch(
            "scheduler.context.AppContext.services.octopoes.get_findings_by_ooi",
        ).start()

        self.tree_response = json.load(
            Path("tests/fixtures/api_responses/octopoes_get_tree.json").open(encoding="utf-8"),
        )

    def test_parse_findings(self):
        findings = services.Octopoes.findings_from_tree_response(self.tree_response)
        self.assertEqual(len(findings), 3)

    def test_parse_objects(self):
        objects = services.Octopoes.objects_from_tree_response(self.tree_response)
        self.assertEqual(len(objects), 10)

    def test_rank(self):
        # Arrange
        scan_profile = factories.ScanProfileFactory(level=0)
        ooi = factories.OOIFactory(scan_profile=scan_profile)
        boefje = factories.BoefjeFactory()
        boefje_task = models.BoefjeTask(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        scheduler_id = uuid.uuid4().hex
        prior_tasks = []

        num_tasks = 10
        for i in range(num_tasks):
            fuzzy_datetime = fuzzy.FuzzyDateTime(
                datetime.now(timezone.utc),
                force_day=datetime.now(timezone.utc).day,
            )

            task = models.Task(
                id=uuid.uuid4(),
                scheduler_id=scheduler_id,
                type="boefje",
                p_item=models.PrioritizedItem(
                    scheduler_id=scheduler_id,
                    hash=mmh3.hash_bytes(f"hash-{i}").hex(),
                    priority=random.randint(1, 100),
                    data=boefje_task.dict(),
                ),
                status=models.TaskStatus.QUEUED,
                created_at=fuzzy_datetime.start_dt,
                modified_at=fuzzy_datetime.end_dt,
            )
            prior_tasks.append(task)

        def generate_random_elements(*args, **kwargs):
            num_elements = random.randint(1, 10)
            elements = [random.randint(1, 100) for _ in range(num_elements)]
            return elements

        # Mock
        self.mock_get_tasks_by_hash.return_value = prior_tasks
        self.mock_get_objects_by_ooi.side_effect = generate_random_elements
        self.mock_get_findings_by_ooi.side_effect = generate_random_elements

        self.ranker.rank(boefje_task)
