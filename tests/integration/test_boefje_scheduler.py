import unittest
import uuid
from datetime import datetime, timedelta, timezone
from unittest import mock

from scheduler import config, connectors, models, queues, rankers, repositories, schedulers
from tests.factories import (
    BoefjeFactory,
    BoefjeMetaFactory,
    OOIFactory,
    OrganisationFactory,
    PluginFactory,
    ScanProfileFactory,
)
from tests.utils import functions


class SchedulerTestCase(unittest.TestCase):
    def setUp(self):
        cfg = config.settings.Settings()

        self.mock_ctx = mock.patch("scheduler.context.AppContext").start()
        self.mock_ctx.config = cfg

        # Mock connectors: octopoes
        self.mock_octopoes = mock.create_autospec(
            spec=connectors.services.Octopoes,
            spec_set=True,
        )
        self.mock_ctx.services.octopoes = self.mock_octopoes

        # Mock connectors: Scan profile mutation
        self.mock_scan_profile_mutation = mock.create_autospec(
            spec=connectors.listeners.ScanProfileMutation,
            spec_set=True,
        )
        self.mock_ctx.services.scan_profile_mutation = self.mock_scan_profile_mutation

        # Mock connectors: Katalogus
        self.mock_katalogus = mock.create_autospec(
            spec=connectors.services.Katalogus,
            spec_set=True,
        )
        self.mock_ctx.services.katalogus = self.mock_katalogus

        # Mock connectors: Bytes
        self.mock_bytes = mock.create_autospec(
            spec=connectors.services.Bytes,
            spec_set=True,
        )
        self.mock_ctx.services.bytes = self.mock_bytes

        # Datastore
        self.mock_ctx.datastore = repositories.sqlalchemy.SQLAlchemy("sqlite:///")
        models.Base.metadata.create_all(self.mock_ctx.datastore.engine)
        self.pq_store = repositories.sqlalchemy.PriorityQueueStore(self.mock_ctx.datastore)
        self.task_store = repositories.sqlalchemy.TaskStore(self.mock_ctx.datastore)

        self.mock_ctx.pq_store = self.pq_store
        self.mock_ctx.task_store = self.task_store

        # Scheduler
        self.organisation = OrganisationFactory()

        queue = queues.BoefjePriorityQueue(
            pq_id=self.organisation.id,
            maxsize=cfg.pq_maxsize,
            item_type=models.BoefjeTask,
            allow_priority_updates=True,
            pq_store=self.pq_store,
        )

        ranker = rankers.BoefjeRanker(
            ctx=self.mock_ctx,
        )

        self.scheduler = schedulers.BoefjeScheduler(
            ctx=self.mock_ctx,
            scheduler_id=self.organisation.id,
            queue=queue,
            ranker=ranker,
            organisation=self.organisation,
        )

    @mock.patch("scheduler.schedulers.BoefjeScheduler.is_task_running")
    @mock.patch("scheduler.schedulers.BoefjeScheduler.is_task_allowed_to_run")
    @mock.patch("scheduler.schedulers.BoefjeScheduler.has_grace_period_passed")
    @mock.patch("scheduler.schedulers.BoefjeScheduler.get_boefjes_for_ooi")
    @mock.patch("scheduler.context.AppContext.services.scan_profile_mutation.get_scan_profile_mutation")
    def test_push_tasks_for_scan_profile_mutations(
        self,
        mock_get_scan_profile_mutation,
        mock_get_boefjes_for_ooi,
        mock_has_grace_period_passed,
        mock_is_task_allowed_to_run,
        mock_is_task_running,
    ):
        """Scan level change"""
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=0, consumes=[ooi.object_type])

        # Mocks
        mock_get_scan_profile_mutation.side_effect = [
            models.ScanProfileMutation(operation="create", primary_key=ooi.primary_key, value=ooi),
            None,
        ]
        mock_get_boefjes_for_ooi.return_value = [boefje]
        mock_is_task_running.return_value = False
        mock_is_task_allowed_to_run.return_value = True
        mock_has_grace_period_passed.return_value = True

        # Act
        self.scheduler.push_tasks_for_scan_profile_mutations()

        # Task should be on priority queue
        task_pq = models.BoefjeTask(**self.scheduler.queue.peek(0).data)
        self.assertEqual(1, self.scheduler.queue.qsize())
        self.assertEqual(ooi.primary_key, task_pq.input_ooi)
        self.assertEqual(boefje.id, task_pq.boefje.id)

        # Task should be in datastore, and queued
        task_db = self.mock_ctx.task_store.get_task_by_id(task_pq.id)
        self.assertEqual(task_db.id.hex, task_pq.id)
        self.assertEqual(task_db.status, models.TaskStatus.QUEUED)

    @mock.patch("scheduler.schedulers.BoefjeScheduler.get_boefjes_for_ooi")
    @mock.patch("scheduler.context.AppContext.services.scan_profile_mutation.get_scan_profile_mutation")
    def test_push_tasks_for_scan_profile_mutations_no_boefjes_found(
        self,
        mock_get_scan_profile_mutation,
        mock_get_boefjes_for_ooi,
    ):
        """When no plugins are found for boefjes, it should return no boefje tasks"""
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)

        # Mocks
        mock_get_scan_profile_mutation.side_effect = [
            models.ScanProfileMutation(operation="create", primary_key=ooi.primary_key, value=ooi),
            None,
        ]
        mock_get_boefjes_for_ooi.return_value = []

        # Act
        self.scheduler.push_tasks_for_scan_profile_mutations()

        # Task should not be on priority queue
        self.assertEqual(0, self.scheduler.queue.qsize())

    @mock.patch("scheduler.schedulers.BoefjeScheduler.is_task_running")
    @mock.patch("scheduler.schedulers.BoefjeScheduler.is_task_allowed_to_run")
    @mock.patch("scheduler.schedulers.BoefjeScheduler.get_boefjes_for_ooi")
    @mock.patch("scheduler.context.AppContext.services.scan_profile_mutation.get_scan_profile_mutation")
    def test_push_tasks_for_scan_profile_mutations_not_allowed_to_run(
        self,
        mock_get_scan_profile_mutation,
        mock_get_boefjes_for_ooi,
        mock_is_task_allowed_to_run,
        mock_is_task_running,
    ):
        """When a boefje is not allowed to run, it should not be added to the queue"""
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=0, consumes=[ooi.object_type])

        # Mocks
        mock_get_scan_profile_mutation.side_effect = [
            models.ScanProfileMutation(operation="create", primary_key=ooi.primary_key, value=ooi),
            None,
        ]
        mock_get_boefjes_for_ooi.return_value = [boefje]
        mock_is_task_allowed_to_run.return_value = False
        mock_is_task_running.return_value = False

        # Act
        self.scheduler.push_tasks_for_scan_profile_mutations()

        # Task should not be on priority queue
        self.assertEqual(0, self.scheduler.queue.qsize())

    @mock.patch("scheduler.schedulers.BoefjeScheduler.is_task_running")
    @mock.patch("scheduler.schedulers.BoefjeScheduler.is_task_allowed_to_run")
    @mock.patch("scheduler.schedulers.BoefjeScheduler.get_boefjes_for_ooi")
    @mock.patch("scheduler.context.AppContext.services.scan_profile_mutation.get_scan_profile_mutation")
    def test_push_tasks_for_scan_profile_mutations_still_running(
        self,
        mock_get_scan_profile_mutation,
        mock_get_boefjes_for_ooi,
        mock_is_task_allowed_to_run,
        mock_is_task_running,
    ):
        """When a boefje is still running, it should not be added to the queue"""
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=0, consumes=[ooi.object_type])

        # Mocks
        mock_get_scan_profile_mutation.side_effect = [
            models.ScanProfileMutation(operation="create", primary_key=ooi.primary_key, value=ooi),
            None,
        ]
        mock_get_boefjes_for_ooi.return_value = [boefje]
        mock_is_task_allowed_to_run.return_value = True
        mock_is_task_running.return_value = True

        # Act
        self.scheduler.push_tasks_for_scan_profile_mutations()

        # Task should not be on priority queue
        self.assertEqual(0, self.scheduler.queue.qsize())

    @mock.patch("scheduler.schedulers.BoefjeScheduler.is_task_running")
    @mock.patch("scheduler.schedulers.BoefjeScheduler.is_task_allowed_to_run")
    @mock.patch("scheduler.schedulers.BoefjeScheduler.has_grace_period_passed")
    @mock.patch("scheduler.schedulers.BoefjeScheduler.get_boefjes_for_ooi")
    @mock.patch("scheduler.context.AppContext.services.scan_profile_mutation.get_scan_profile_mutation")
    def test_push_tasks_for_scan_profile_mutations_item_on_queue(
        self,
        mock_get_scan_profile_mutation,
        mock_get_boefjes_for_ooi,
        mock_has_grace_period_passed,
        mock_is_task_allowed_to_run,
        mock_is_task_running,
    ):
        """When a boefje is already on the queue, it should not be added to the queue"""
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=0, consumes=[ooi.object_type])

        # Mocks
        mock_get_scan_profile_mutation.side_effect = [
            models.ScanProfileMutation(operation="create", primary_key=ooi.primary_key, value=ooi),
            models.ScanProfileMutation(operation="update", primary_key=ooi.primary_key, value=ooi),
            None,
        ]
        mock_get_boefjes_for_ooi.return_value = [boefje]
        mock_is_task_running.return_value = False
        mock_is_task_allowed_to_run.return_value = True
        mock_has_grace_period_passed.return_value = True

        # Act
        self.scheduler.push_tasks_for_scan_profile_mutations()

        # Task should be on priority queue
        task_pq = models.BoefjeTask(**self.scheduler.queue.peek(0).data)
        self.assertEqual(1, self.scheduler.queue.qsize())
        self.assertEqual(ooi.primary_key, task_pq.input_ooi)
        self.assertEqual(boefje.id, task_pq.boefje.id)

        # Task should be in datastore, and queued
        task_db = self.mock_ctx.task_store.get_task_by_id(task_pq.id)
        self.assertEqual(task_db.id.hex, task_pq.id)
        self.assertEqual(task_db.status, models.TaskStatus.QUEUED)

    @mock.patch("scheduler.schedulers.BoefjeScheduler.is_task_running")
    @mock.patch("scheduler.schedulers.BoefjeScheduler.is_task_allowed_to_run")
    @mock.patch("scheduler.schedulers.BoefjeScheduler.has_grace_period_passed")
    @mock.patch("scheduler.schedulers.BoefjeScheduler.get_boefjes_for_ooi")
    @mock.patch("scheduler.context.AppContext.services.octopoes.get_random_objects")
    def test_push_tasks_for_random_objects(
        self,
        mock_get_random_objects,
        mock_get_boefjes_for_ooi,
        mock_has_grace_period_passed,
        mock_is_task_allowed_to_run,
        mock_is_task_running,
    ):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=0, consumes=[ooi.object_type])

        # Mocks
        mock_get_random_objects.side_effect = [[ooi], [], [], []]
        mock_get_boefjes_for_ooi.return_value = [boefje]
        mock_is_task_running.return_value = False
        mock_is_task_allowed_to_run.return_value = True
        mock_has_grace_period_passed.return_value = True

        # Act
        self.scheduler.push_tasks_for_random_objects()

        # Task should be on priority queue
        task_pq = models.BoefjeTask(**self.scheduler.queue.peek(0).data)
        self.assertEqual(1, self.scheduler.queue.qsize())
        self.assertEqual(ooi.primary_key, task_pq.input_ooi)
        self.assertEqual(boefje.id, task_pq.boefje.id)

        # Task should be in datastore, and queued
        task_db = self.mock_ctx.task_store.get_task_by_id(task_pq.id)
        self.assertEqual(task_db.id.hex, task_pq.id)
        self.assertEqual(task_db.status, models.TaskStatus.QUEUED)

    @mock.patch("scheduler.schedulers.BoefjeScheduler.get_boefjes_for_ooi")
    @mock.patch("scheduler.context.AppContext.services.octopoes.get_random_objects")
    def test_push_tasks_for_random_objects_no_boefjes_found(
        self,
        mock_get_random_objects,
        mock_get_boefjes_for_ooi,
    ):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)

        # Mocks
        mock_get_random_objects.side_effect = [[ooi], [], [], []]
        mock_get_boefjes_for_ooi.return_value = []

        # Act
        self.scheduler.push_tasks_for_random_objects()

        # Task should not be on priority queue
        self.assertEqual(0, self.scheduler.queue.qsize())

    @mock.patch("scheduler.schedulers.BoefjeScheduler.is_task_running")
    @mock.patch("scheduler.schedulers.BoefjeScheduler.is_task_allowed_to_run")
    @mock.patch("scheduler.schedulers.BoefjeScheduler.get_boefjes_for_ooi")
    @mock.patch("scheduler.context.AppContext.services.octopoes.get_random_objects")
    def test_push_tasks_for_random_objects_not_allowed_to_run(
        self, mock_get_random_objects, mock_get_boefjes_for_ooi, mock_is_task_allowed_to_run, mock_is_task_running
    ):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=0, consumes=[ooi.object_type])

        # Mocks
        mock_get_random_objects.side_effect = [[ooi], [], [], []]
        mock_get_boefjes_for_ooi.return_value = [boefje]
        mock_is_task_allowed_to_run.return_value = False
        mock_is_task_running.return_value = False

        # Act
        self.scheduler.push_tasks_for_random_objects()

        # Task should not be on priority queue
        self.assertEqual(0, self.scheduler.queue.qsize())

    @mock.patch("scheduler.schedulers.BoefjeScheduler.is_task_running")
    @mock.patch("scheduler.schedulers.BoefjeScheduler.is_task_allowed_to_run")
    @mock.patch("scheduler.schedulers.BoefjeScheduler.has_grace_period_passed")
    @mock.patch("scheduler.schedulers.BoefjeScheduler.get_boefjes_for_ooi")
    @mock.patch("scheduler.context.AppContext.services.octopoes.get_random_objects")
    def test_push_tasks_for_random_objects_still_running(
        self,
        mock_get_random_objects,
        mock_get_boefjes_for_ooi,
        mock_has_grace_period_passed,
        mock_is_task_allowed_to_run,
        mock_is_task_running,
    ):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=0, consumes=[ooi.object_type])

        # Mocks
        mock_get_random_objects.side_effect = [[ooi], [], [], []]
        mock_get_boefjes_for_ooi.return_value = [boefje]
        mock_is_task_allowed_to_run.return_value = True
        mock_is_task_running.return_value = True
        mock_has_grace_period_passed.return_value = True

        # Act
        self.scheduler.push_tasks_for_random_objects()

        # Task should not be on priority queue
        self.assertEqual(0, self.scheduler.queue.qsize())

    @mock.patch("scheduler.schedulers.BoefjeScheduler.is_task_running")
    @mock.patch("scheduler.schedulers.BoefjeScheduler.is_task_allowed_to_run")
    @mock.patch("scheduler.schedulers.BoefjeScheduler.has_grace_period_passed")
    @mock.patch("scheduler.schedulers.BoefjeScheduler.get_boefjes_for_ooi")
    @mock.patch("scheduler.context.AppContext.services.octopoes.get_random_objects")
    def test_push_tasks_for_random_objects_item_on_queue(
        self,
        mock_get_random_objects,
        mock_get_boefjes_for_ooi,
        mock_has_grace_period_passed,
        mock_is_task_allowed_to_run,
        mock_is_task_running,
    ):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=0, consumes=[ooi.object_type])

        # Mocks
        mock_get_random_objects.side_effect = [[ooi], [ooi], [], []]
        mock_get_boefjes_for_ooi.return_value = [boefje]
        mock_is_task_allowed_to_run.return_value = True
        mock_is_task_running.return_value = False
        mock_has_grace_period_passed.return_value = True

        # Act
        self.scheduler.push_tasks_for_random_objects()

        # Task should be on priority queue
        task_pq = models.BoefjeTask(**self.scheduler.queue.peek(0).data)
        self.assertEqual(1, self.scheduler.queue.qsize())
        self.assertEqual(ooi.primary_key, task_pq.input_ooi)
        self.assertEqual(boefje.id, task_pq.boefje.id)

        # Task should be in datastore, and queueud
        task_db = self.mock_ctx.task_store.get_task_by_id(task_pq.id)
        self.assertEqual(task_db.id.hex, task_pq.id)
        self.assertEqual(task_db.status, models.TaskStatus.QUEUED)

    @mock.patch("scheduler.schedulers.BoefjeScheduler.is_task_running")
    @mock.patch("scheduler.schedulers.BoefjeScheduler.is_task_allowed_to_run")
    @mock.patch("scheduler.schedulers.BoefjeScheduler.has_grace_period_passed")
    @mock.patch("scheduler.schedulers.BoefjeScheduler.get_boefjes_for_ooi")
    @mock.patch("scheduler.context.AppContext.services.octopoes.get_random_objects")
    def test_push_tasks_for_random_objects_everything_processed(
        self,
        mock_get_random_objects,
        mock_get_boefjes_for_ooi,
        mock_has_grace_period_passed,
        mock_is_task_allowed_to_run,
        mock_is_task_running,
    ):
        """Test if the scheduler stops when there are no more objects to
        process.

        We simulate this by returning the same ooi from the random object
        endpoint. This will create the same tasks and should not be added to
        the queue. And should fall into the grace period.
        """
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=0, consumes=[ooi.object_type])

        # Mocks
        mock_get_random_objects.return_value = [ooi]
        mock_get_boefjes_for_ooi.return_value = [boefje]
        mock_is_task_running.return_value = False
        mock_has_grace_period_passed.return_value = True

        # Simulate for the first iteration the task is allowed to run
        # and the subsequent iterations are not.
        mock_is_task_allowed_to_run.side_effect = [True, False, False, False]

        # Act
        with self.assertLogs("scheduler.schedulers", level="DEBUG") as cm:
            self.scheduler.push_tasks_for_random_objects()

        # Assert we have 3 tries
        self.assertIn("No tasks generated for 3 tries", cm.output[-1])

        # Task should be on priority queue
        task_pq = models.BoefjeTask(**self.scheduler.queue.peek(0).data)
        self.assertEqual(1, self.scheduler.queue.qsize())
        self.assertEqual(ooi.primary_key, task_pq.input_ooi)
        self.assertEqual(boefje.id, task_pq.boefje.id)

        # Task should be in datastore, and queueud
        task_db = self.mock_ctx.task_store.get_task_by_id(task_pq.id)
        self.assertEqual(task_db.id.hex, task_pq.id)
        self.assertEqual(task_db.status, models.TaskStatus.QUEUED)

    def test_is_allowed_to_run(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=0, consumes=[ooi.object_type])

        # Act
        allowed_to_run = self.scheduler.is_task_allowed_to_run(ooi=ooi, boefje=boefje)

        # Assert
        self.assertTrue(allowed_to_run)

    def test_is_not_allowed_to_run(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=4, consumes=[ooi.object_type])

        # Act
        with self.assertLogs("scheduler.schedulers", level="DEBUG") as cm:
            allowed_to_run = self.scheduler.is_task_allowed_to_run(ooi=ooi, boefje=boefje)

        # Assert
        self.assertFalse(allowed_to_run)
        self.assertIn("is too intense", cm.output[-1])

    @mock.patch("scheduler.context.AppContext.task_store.get_latest_task_by_hash")
    @mock.patch("scheduler.context.AppContext.services.bytes.get_last_run_boefje")
    def test_is_task_not_running(self, mock_get_last_run_boefje, mock_get_latest_task_by_hash):
        """When both the task cannot be found in the datastore and bytes
        the task is not running.
        """
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=0, consumes=[ooi.object_type])
        task = models.BoefjeTask(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        # Mock
        mock_get_latest_task_by_hash.return_value = None
        mock_get_last_run_boefje.return_value = None

        # Act
        is_running = self.scheduler.is_task_running(task)

        # Assert
        self.assertFalse(is_running)

    @mock.patch("scheduler.context.AppContext.task_store.get_latest_task_by_hash")
    @mock.patch("scheduler.context.AppContext.services.bytes.get_last_run_boefje")
    def test_is_task_running_datastore_running(self, mock_get_last_run_boefje, mock_get_latest_task_by_hash):
        """When the task is found in the datastore and the status isn't
        failed or completed, then the task is still running.
        """
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=0, consumes=[ooi.object_type])
        task = models.BoefjeTask(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        p_item = models.PrioritizedItem(
            id=task.id,
            scheduler_id=self.scheduler.scheduler_id,
            priority=1,
            data=task,
            hash=task.hash,
        )

        task_db = models.Task(
            id=p_item.id,
            scheduler_id=self.scheduler.scheduler_id,
            type="boefje",
            p_item=p_item,
            status=models.TaskStatus.QUEUED,
            created_at=datetime.utcnow(),
            modified_at=datetime.utcnow(),
        )

        # Mock
        mock_get_latest_task_by_hash.return_value = task_db
        mock_get_last_run_boefje.return_value = None

        # Act
        is_running = self.scheduler.is_task_running(task)

        # Assert
        self.assertTrue(is_running)

    @mock.patch("scheduler.context.AppContext.task_store.get_latest_task_by_hash")
    @mock.patch("scheduler.context.AppContext.services.bytes.get_last_run_boefje")
    def test_is_task_running_datastore_not_running(self, mock_get_last_run_boefje, mock_get_latest_task_by_hash):
        """When the task is found in the datastore and the status is
        failed or completed, then the task is not running.
        """
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=0, consumes=[ooi.object_type])
        task = models.BoefjeTask(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        p_item = models.PrioritizedItem(
            id=task.id,
            scheduler_id=self.scheduler.scheduler_id,
            priority=1,
            data=task,
            hash=task.hash,
        )

        task_db_first = models.Task(
            id=p_item.id,
            scheduler_id=self.scheduler.scheduler_id,
            type="boefje",
            p_item=p_item,
            status=models.TaskStatus.COMPLETED,
            created_at=datetime.utcnow(),
            modified_at=datetime.utcnow(),
        )

        task_db_second = models.Task(
            id=p_item.id,
            scheduler_id=self.scheduler.scheduler_id,
            type="boefje",
            p_item=p_item,
            status=models.TaskStatus.FAILED,
            created_at=datetime.utcnow(),
            modified_at=datetime.utcnow(),
        )

        last_run_boefje = BoefjeMetaFactory(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            ended_at=datetime.utcnow(),
        )

        # Mock
        mock_get_latest_task_by_hash.side_effect = [
            task_db_first,
            task_db_second,
        ]
        mock_get_last_run_boefje.return_value = last_run_boefje

        # First run
        is_running = self.scheduler.is_task_running(task)
        self.assertFalse(is_running)

        # Second run
        is_running = self.scheduler.is_task_running(task)
        self.assertFalse(is_running)

    @mock.patch("scheduler.context.AppContext.task_store.get_latest_task_by_hash")
    @mock.patch("scheduler.context.AppContext.services.bytes.get_last_run_boefje")
    def test_is_task_running_bytes_running(self, mock_get_last_run_boefje, mock_get_latest_task_by_hash):
        """When task is found in bytes and the started_at field is not None, and
        the ended_at field is None. The task is still running."""
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=0, consumes=[ooi.object_type])
        task = models.BoefjeTask(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )
        last_run_boefje = BoefjeMetaFactory(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            ended_at=None,
        )

        # Mock
        mock_get_latest_task_by_hash.return_value = None
        mock_get_last_run_boefje.return_value = last_run_boefje

        # Act
        is_running = self.scheduler.is_task_running(task)

        # Assert
        self.assertTrue(is_running)

    @mock.patch("scheduler.context.AppContext.task_store.get_latest_task_by_hash")
    @mock.patch("scheduler.context.AppContext.services.bytes.get_last_run_boefje")
    def test_is_task_running_bytes_not_running(self, mock_get_last_run_boefje, mock_get_latest_task_by_hash):
        """When task is found in bytes and the started_at field is not None, and
        the ended_at field is not None. The task is not running."""
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=0, consumes=[ooi.object_type])
        task = models.BoefjeTask(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )
        last_run_boefje = BoefjeMetaFactory(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            ended_at=datetime.utcnow(),
        )

        # Mock
        mock_get_latest_task_by_hash.return_value = None
        mock_get_last_run_boefje.return_value = last_run_boefje

        # Act
        is_running = self.scheduler.is_task_running(task)

        # Assert
        self.assertFalse(is_running)

    @mock.patch("scheduler.context.AppContext.task_store.get_latest_task_by_hash")
    @mock.patch("scheduler.context.AppContext.services.bytes.get_last_run_boefje")
    def test_is_task_running_mismatch(
        self,
        mock_get_last_run_boefje,
        mock_get_latest_task_by_hash,
    ):
        """When a task has finished according to the datastore, (e.g. failed
        or completed), but there are no results in bytes, we have a problem.
        """
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=0, consumes=[ooi.object_type])
        task = models.BoefjeTask(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        p_item = models.PrioritizedItem(
            id=task.id,
            scheduler_id=self.scheduler.scheduler_id,
            priority=1,
            data=task,
            hash=task.hash,
        )

        task_db = models.Task(
            id=p_item.id,
            scheduler_id=self.scheduler.scheduler_id,
            type="boefje",
            p_item=p_item,
            status=models.TaskStatus.COMPLETED,
            created_at=datetime.utcnow(),
            modified_at=datetime.utcnow(),
        )

        # Mock
        mock_get_latest_task_by_hash.return_value = task_db
        mock_get_last_run_boefje.return_value = None

        # Act
        with self.assertRaises(RuntimeError):
            self.scheduler.is_task_running(task)

    @mock.patch("scheduler.context.AppContext.task_store.get_latest_task_by_hash")
    @mock.patch("scheduler.context.AppContext.services.bytes.get_last_run_boefje")
    def test_has_grace_period_passed_datastore_passed(
        self,
        mock_get_last_run_boefje,
        mock_get_latest_task_by_hash,
    ):
        """Grace period passed according to datastore, and the status is completed"""
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=0, consumes=[ooi.object_type])
        task = models.BoefjeTask(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        p_item = models.PrioritizedItem(
            id=task.id,
            scheduler_id=self.scheduler.scheduler_id,
            priority=1,
            data=task,
            hash=task.hash,
        )

        task_db = models.Task(
            id=p_item.id,
            scheduler_id=self.scheduler.scheduler_id,
            type="boefje",
            p_item=p_item,
            status=models.TaskStatus.COMPLETED,
            created_at=datetime.utcnow(),
            modified_at=datetime.utcnow() - timedelta(seconds=self.mock_ctx.config.pq_populate_grace_period),
        )

        # Mock
        mock_get_latest_task_by_hash.return_value = task_db
        mock_get_last_run_boefje.return_value = None

        # Act
        has_passed = self.scheduler.has_grace_period_passed(task)

        # Assert
        self.assertTrue(has_passed)

    @mock.patch("scheduler.context.AppContext.task_store.get_latest_task_by_hash")
    @mock.patch("scheduler.context.AppContext.services.bytes.get_last_run_boefje")
    def test_has_grace_period_passed_datastore_not_passed(
        self,
        mock_get_last_run_boefje,
        mock_get_latest_task_by_hash,
    ):
        """Grace period not passed according to datastore."""
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=0, consumes=[ooi.object_type])
        task = models.BoefjeTask(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        p_item = models.PrioritizedItem(
            id=task.id,
            scheduler_id=self.scheduler.scheduler_id,
            priority=1,
            data=task,
            hash=task.hash,
        )

        task_db = models.Task(
            id=p_item.id,
            scheduler_id=self.scheduler.scheduler_id,
            type="boefje",
            p_item=p_item,
            status=models.TaskStatus.COMPLETED,
            created_at=datetime.utcnow(),
            modified_at=datetime.utcnow(),
        )

        # Mock
        mock_get_latest_task_by_hash.return_value = task_db
        mock_get_last_run_boefje.return_value = None

        # Act
        has_passed = self.scheduler.has_grace_period_passed(task)

        # Assert
        self.assertFalse(has_passed)

    @mock.patch("scheduler.context.AppContext.task_store.get_latest_task_by_hash")
    @mock.patch("scheduler.context.AppContext.services.bytes.get_last_run_boefje")
    def test_has_grace_period_passed_bytes_passed(
        self,
        mock_get_last_run_boefje,
        mock_get_latest_task_by_hash,
    ):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=0, consumes=[ooi.object_type])
        task = models.BoefjeTask(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        p_item = models.PrioritizedItem(
            id=task.id,
            scheduler_id=self.scheduler.scheduler_id,
            priority=1,
            data=task,
            hash=task.hash,
        )

        task_db = models.Task(
            id=p_item.id,
            scheduler_id=self.scheduler.scheduler_id,
            type="boefje",
            p_item=p_item,
            status=models.TaskStatus.COMPLETED,
            created_at=datetime.utcnow(),
            modified_at=datetime.utcnow() - timedelta(seconds=self.mock_ctx.config.pq_populate_grace_period),
        )

        last_run_boefje = BoefjeMetaFactory(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            ended_at=datetime.now(timezone.utc) - timedelta(seconds=self.mock_ctx.config.pq_populate_grace_period),
        )

        # Mock
        mock_get_latest_task_by_hash.return_value = task_db
        mock_get_last_run_boefje.return_value = last_run_boefje

        # Act
        has_passed = self.scheduler.has_grace_period_passed(task)

        # Assert
        self.assertTrue(has_passed)

    @mock.patch("scheduler.context.AppContext.task_store.get_latest_task_by_hash")
    @mock.patch("scheduler.context.AppContext.services.bytes.get_last_run_boefje")
    def test_has_grace_period_passed_bytes_not_passed(
        self,
        mock_get_last_run_boefje,
        mock_get_latest_task_by_hash,
    ):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=0, consumes=[ooi.object_type])
        task = models.BoefjeTask(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        p_item = models.PrioritizedItem(
            id=task.id,
            scheduler_id=self.scheduler.scheduler_id,
            priority=1,
            data=task,
            hash=task.hash,
        )

        task_db = models.Task(
            id=p_item.id,
            scheduler_id=self.scheduler.scheduler_id,
            type="boefje",
            p_item=p_item,
            status=models.TaskStatus.COMPLETED,
            created_at=datetime.utcnow(),
            modified_at=datetime.utcnow() - timedelta(seconds=self.mock_ctx.config.pq_populate_grace_period),
        )

        last_run_boefje = BoefjeMetaFactory(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            ended_at=datetime.now(timezone.utc),
        )

        # Mock
        mock_get_latest_task_by_hash.return_value = task_db
        mock_get_last_run_boefje.return_value = last_run_boefje

        # Act
        has_passed = self.scheduler.has_grace_period_passed(task)

        # Assert
        self.assertFalse(has_passed)

    @mock.patch("scheduler.schedulers.BoefjeScheduler.has_grace_period_passed")
    @mock.patch("scheduler.schedulers.BoefjeScheduler.is_task_running")
    @mock.patch("scheduler.schedulers.BoefjeScheduler.is_task_allowed_to_run")
    @mock.patch("scheduler.schedulers.BoefjeScheduler.get_boefjes_for_ooi")
    @mock.patch("scheduler.context.AppContext.services.scan_profile_mutation.get_scan_profile_mutation")
    @mock.patch("scheduler.context.AppContext.services.octopoes.get_random_objects")
    def test_populate_queue_random_objects(
        self,
        mock_get_random_objects,
        mock_get_scan_profile_mutation,
        mock_get_boefjes_for_ooi,
        mock_is_task_allowed_to_run,
        mock_is_task_running,
        mock_has_grace_period_passed,
    ):
        """When no scan profile mutations are present, it should be filled up
        with random oois"""
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=0, consumes=[ooi.object_type])

        # Mocks
        mock_get_random_objects.side_effect = [[ooi], [], [], []]
        mock_get_scan_profile_mutation.return_value = None
        mock_get_boefjes_for_ooi.return_value = [boefje]
        mock_is_task_running.return_value = False
        mock_is_task_allowed_to_run.return_value = True
        mock_has_grace_period_passed.return_value = True

        # Act
        self.scheduler.populate_queue()

        # Task should be on priority queue
        task_pq = models.BoefjeTask(**self.scheduler.queue.peek(0).data)
        self.assertEqual(1, self.scheduler.queue.qsize())
        self.assertEqual(ooi.primary_key, task_pq.input_ooi)
        self.assertEqual(boefje.id, task_pq.boefje.id)

        # Task should be in datastore, and queued
        task_db = self.mock_ctx.task_store.get_task_by_id(task_pq.id)
        self.assertEqual(task_db.id.hex, task_pq.id)
        self.assertEqual(task_db.status, models.TaskStatus.QUEUED)

    @mock.patch("scheduler.schedulers.BoefjeScheduler.push_tasks_for_random_objects")
    @mock.patch("scheduler.schedulers.BoefjeScheduler.has_grace_period_passed")
    @mock.patch("scheduler.schedulers.BoefjeScheduler.is_task_running")
    @mock.patch("scheduler.schedulers.BoefjeScheduler.is_task_allowed_to_run")
    @mock.patch("scheduler.schedulers.BoefjeScheduler.get_boefjes_for_ooi")
    @mock.patch("scheduler.context.AppContext.services.scan_profile_mutation.get_scan_profile_mutation")
    def test_populate_queue_scan_profile_mutations(
        self,
        mock_get_scan_profile_mutation,
        mock_get_boefjes_for_ooi,
        mock_is_task_allowed_to_run,
        mock_is_task_running,
        mock_has_grace_period_passed,
        mock_push_tasks_for_random_objects,
    ):
        """Population of queue should start with scan profile mutations"""
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(scan_level=0, consumes=[ooi.object_type])

        # Mocks
        mock_get_scan_profile_mutation.side_effect = [
            models.ScanProfileMutation(operation="create", primary_key=ooi.primary_key, value=ooi),
            None,
        ]
        mock_get_boefjes_for_ooi.return_value = [boefje]
        mock_is_task_running.return_value = False
        mock_is_task_allowed_to_run.return_value = True
        mock_has_grace_period_passed.return_value = True
        mock_push_tasks_for_random_objects.return_value = None

        # Act
        self.scheduler.populate_queue()

        # Task should be on priority queue
        task_pq = models.BoefjeTask(**self.scheduler.queue.peek(0).data)
        self.assertEqual(1, self.scheduler.queue.qsize())
        self.assertEqual(ooi.primary_key, task_pq.input_ooi)
        self.assertEqual(boefje.id, task_pq.boefje.id)

        # Task should be in datastore, and queued
        task_db = self.mock_ctx.task_store.get_task_by_id(task_pq.id)
        self.assertEqual(task_db.id.hex, task_pq.id)
        self.assertEqual(task_db.status, models.TaskStatus.QUEUED)

    @mock.patch("scheduler.context.AppContext.services.katalogus.get_boefjes_by_type_and_org_id")
    def test_populate_queue_queue_full(self, mock_get_boefjes_by_type_and_org_id):
        """When the boefje queue is full, it should not return a boefje task"""
        organisation = OrganisationFactory()

        # Make a queue with only one open slot
        queue = queues.BoefjePriorityQueue(
            pq_id=organisation.id,
            maxsize=1,
            item_type=models.BoefjeTask,
            allow_priority_updates=True,
            pq_store=self.pq_store,
        )

        # Add a task to the queue to make it full
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        task = models.BoefjeTask(
            id=uuid.uuid4().hex,
            boefje=BoefjeFactory(),
            input_ooi=ooi.primary_key,
            organization=organisation.id,
        )
        queue.push(functions.create_p_item(scheduler_id=organisation.id, priority=0, data=task))

        self.scheduler.queue = queue

        # Assert
        self.assertEqual(1, self.scheduler.queue.qsize())

        # Act
        self.scheduler.populate_queue()

        # Assert
        self.assertEqual(1, self.scheduler.queue.qsize())

    def test_post_push(self):
        """When a task is added to the queue, it should be added to the database"""
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        task = models.BoefjeTask(
            boefje=BoefjeFactory(),
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )
        p_item = functions.create_p_item(
            scheduler_id=self.organisation.id,
            priority=0,
            data=task,
        )

        # Act
        self.scheduler.push_item_to_queue(p_item)

        # Task should be on priority queue
        task_pq = models.BoefjeTask(**self.scheduler.queue.peek(0).data)
        self.assertEqual(1, self.scheduler.queue.qsize())
        self.assertEqual(ooi.primary_key, task_pq.input_ooi)
        self.assertEqual(task.boefje.id, task_pq.boefje.id)

        # Task should be in datastore, and queued
        task_db = self.mock_ctx.task_store.get_task_by_id(p_item.id)
        self.assertEqual(task_db.id, p_item.id)
        self.assertEqual(task_db.status, models.TaskStatus.QUEUED)

    def test_post_pop(self):
        """When a task is removed from the queue, its status should be updated"""
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        task = models.BoefjeTask(
            boefje=BoefjeFactory(),
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )
        p_item = functions.create_p_item(
            scheduler_id=self.organisation.id,
            priority=0,
            data=task,
        )

        # Act
        self.scheduler.push_item_to_queue(p_item)

        # Assert: task should be on priority queue
        task_pq = models.BoefjeTask(**self.scheduler.queue.peek(0).data)
        self.assertEqual(1, self.scheduler.queue.qsize())
        self.assertEqual(ooi.primary_key, task_pq.input_ooi)
        self.assertEqual(task.boefje.id, task_pq.boefje.id)

        # Assert: task should be in datastore, and queued
        task_db = self.mock_ctx.task_store.get_task_by_id(p_item.id)
        self.assertEqual(task_db.id, p_item.id)
        self.assertEqual(task_db.status, models.TaskStatus.QUEUED)

        # Act
        self.scheduler.pop_item_from_queue()

        # Assert: task should be in datastore, and dispatched
        task_db = self.mock_ctx.task_store.get_task_by_id(p_item.id)
        self.assertEqual(task_db.id, p_item.id)
        self.assertEqual(task_db.status, models.TaskStatus.DISPATCHED)
