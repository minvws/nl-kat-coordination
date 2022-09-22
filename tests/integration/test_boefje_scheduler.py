import unittest
import uuid
from datetime import datetime, timedelta, timezone
from unittest import mock

from scheduler import config, connectors, datastores, models, queues, rankers, schedulers
from tests.factories import (
    BoefjeFactory,
    BoefjeMetaFactory,
    OOIFactory,
    OrganisationFactory,
    PluginFactory,
    ScanProfileFactory,
)


class SchedulerTestCase(unittest.TestCase):
    def setUp(self):
        cfg = config.settings.Settings()

        self.mock_ctx = mock.patch("scheduler.context.AppContext").start()
        self.mock_ctx.config = cfg

        # Mock connectors: octopoes
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)

        self.mock_octopoes = mock.create_autospec(
            spec=connectors.services.Octopoes,
            spec_set=True,
        )
        self.mock_ctx.services.octopoes = self.mock_octopoes

        # Mock connectors: Scan profiles
        self.mock_scan_profiles = mock.create_autospec(
            spec=connectors.listeners.ScanProfile,
            spec_set=True,
        )
        self.mock_ctx.services.scan_profile = self.mock_scan_profiles

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
        self.mock_ctx.datastore = datastores.SQLAlchemy(dsn="sqlite:///")
        models.Base.metadata.create_all(self.mock_ctx.datastore.engine)

        # Scheduler
        self.organisation = OrganisationFactory()

        queue = queues.BoefjePriorityQueue(
            pq_id=self.organisation.id,
            maxsize=cfg.pq_maxsize,
            item_type=models.BoefjeTask,
            allow_priority_updates=True,
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

    @mock.patch("scheduler.context.AppContext.services.scan_profile.get_latest_object")
    @mock.patch("scheduler.context.AppContext.services.octopoes.get_random_objects")
    @mock.patch("scheduler.schedulers.BoefjeScheduler.create_tasks_for_oois")
    def test_populate_boefjes_queue_get_latest_object(
        self, mock_create_tasks_for_oois, mock_get_random_objects, mock_get_latest_object
    ):
        """When oois are available, and no random oois"""
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        task = models.BoefjeTask(
            id=uuid.uuid4().hex,
            boefje=BoefjeFactory(),
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        mock_get_latest_object.side_effect = [ooi, None]
        mock_get_random_objects.return_value = []
        mock_create_tasks_for_oois.side_effect = [
            [
                queues.PrioritizedItem(
                    priority=0,
                    item=task,
                )
            ],
        ]

        self.scheduler.populate_queue()
        self.assertEqual(1, self.scheduler.queue.qsize())
        self.assertEqual(task, self.scheduler.queue.peek(0).p_item.item)

    # TODO
    def test_populate_boefjes_queue_overflow(self):
        """One ooi has too many boefjes to fit in the queue"""
        pass

    @mock.patch("scheduler.context.AppContext.services.scan_profile.get_latest_object")
    @mock.patch("scheduler.context.AppContext.services.octopoes.get_random_objects")
    @mock.patch("scheduler.schedulers.BoefjeScheduler.create_tasks_for_oois")
    def test_populate_boefjes_queue_with_no_oois(
        self, mock_create_tasks_for_oois, mock_get_random_objects, mock_get_latest_object
    ):
        """When no oois are available, it should be filled up with random oois"""
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        task = models.BoefjeTask(
            id=uuid.uuid4().hex,
            boefje=BoefjeFactory(),
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        mock_get_latest_object.return_value = None
        mock_get_random_objects.side_effect = [[ooi], [], [], []]
        mock_create_tasks_for_oois.return_value = [
            queues.PrioritizedItem(0, task),
        ]

        self.scheduler.populate_queue()
        self.assertEqual(1, self.scheduler.queue.qsize())
        self.assertEqual(task, self.scheduler.queue.peek(0).p_item.item)

    @mock.patch("scheduler.context.AppContext.services.bytes.get_last_run_boefje")
    @mock.patch("scheduler.context.AppContext.services.katalogus.get_boefjes_by_type_and_org_id")
    def test_create_tasks_for_oois(self, mock_get_boefjes_by_type_and_org_id, mock_get_last_run_boefje):
        """Provided with oois it should return Boefje tasks"""
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefjes = [PluginFactory(type="boefje", scan_level=0) for _ in range(3)]
        last_run_boefje = BoefjeMetaFactory(
            boefje=boefjes[0],
            input_ooi=ooi.primary_key,
            ended_at=datetime.now(timezone.utc) - timedelta(days=1),
        )

        mock_get_boefjes_by_type_and_org_id.return_value = boefjes
        mock_get_last_run_boefje.return_value = last_run_boefje

        tasks = self.scheduler.create_tasks_for_oois([ooi])
        self.assertEqual(3, len(tasks))

    @mock.patch("scheduler.context.AppContext.services.katalogus.get_boefjes_by_type_and_org_id")
    def test_create_tasks_for_oois_plugin_not_found(self, mock_get_boefjes_by_type_and_org_id):
        """When no plugins are found for boefjes, it should return no boefje tasks"""
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefjes = [PluginFactory(type="boefje") for _ in range(3)]

        mock_get_boefjes_by_type_and_org_id.return_value = boefjes

        tasks = self.scheduler.create_tasks_for_oois([ooi])
        self.assertEqual(0, len(tasks))

    @mock.patch("scheduler.context.AppContext.services.katalogus.get_boefjes_by_type_and_org_id")
    def test_create_tasks_for_oois_plugin_disabled(self, mock_get_boefjes_by_type_and_org_id):
        """When a plugin is disabled, it should not return a boefje task"""
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefjes = [PluginFactory(type="boefje", scan_level=0, enabled=False) for _ in range(3)]

        mock_get_boefjes_by_type_and_org_id.return_value = boefjes

        tasks = self.scheduler.create_tasks_for_oois([ooi])
        self.assertEqual(0, len(tasks))

    @mock.patch("scheduler.context.AppContext.services.katalogus.get_boefjes_by_type_and_org_id")
    def test_create_tasks_for_oois_no_boefjes(self, mock_get_boefjes_by_type_and_org_id):
        """When no boefjes are found for oois, it should return no boefje tasks"""
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)

        mock_get_boefjes_by_type_and_org_id.return_value = None

        tasks = self.scheduler.create_tasks_for_oois([ooi])
        self.assertEqual(0, len(tasks))

    @mock.patch("scheduler.context.AppContext.services.katalogus.get_boefjes_by_type_and_org_id")
    def test_create_tasks_for_oois_scan_level_too_intense(self, mock_get_boefjes_by_type_and_org_id):
        """When a boefje scan level is too intense for an ooi, it should not return a boefje task"""
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefjes = [PluginFactory(type="boefje", scan_level=5)]

        mock_get_boefjes_by_type_and_org_id.return_value = boefjes

        tasks = self.scheduler.create_tasks_for_oois([ooi])

        self.assertEqual(0, len(tasks))

    @mock.patch("scheduler.context.AppContext.services.bytes.get_last_run_boefje")
    @mock.patch("scheduler.context.AppContext.services.katalogus.get_boefjes_by_type_and_org_id")
    def test_create_tasks_for_oois_scan_level_allowed(
        self, mock_get_boefjes_by_type_and_org_id, mock_get_last_run_boefje
    ):
        """When a boefje scan level is allowed for an ooi, it should return a boefje task"""
        scan_profile = ScanProfileFactory(level=5)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefjes = [PluginFactory(type="boefje", scan_level=0)]
        last_run_boefje = BoefjeMetaFactory(
            boefje=boefjes[0],
            input_ooi=ooi.primary_key,
            ended_at=datetime.now(timezone.utc) - timedelta(days=1),
        )

        mock_get_boefjes_by_type_and_org_id.return_value = boefjes
        mock_get_last_run_boefje.return_value = last_run_boefje

        tasks = self.scheduler.create_tasks_for_oois([ooi])

        self.assertEqual(1, len(tasks))

    @mock.patch("scheduler.context.AppContext.services.bytes.get_last_run_boefje")
    @mock.patch("scheduler.context.AppContext.services.katalogus.get_boefjes_by_type_and_org_id")
    def test_create_tasks_for_oois_grace_period_not_passed(
        self, mock_get_boefjes_by_type_and_org_id, mock_get_last_run_boefje
    ):
        """When a boefje has been run recently, it should not return a boefje task"""
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefjes = [PluginFactory(type="boefje", scan_level=0)]
        last_run_boefje = BoefjeMetaFactory(
            boefje=boefjes[0],
            input_ooi=ooi.primary_key,
            ended_at=datetime.now(timezone.utc),
        )

        mock_get_boefjes_by_type_and_org_id.return_value = boefjes
        mock_get_last_run_boefje.return_value = last_run_boefje

        # Set grace period for a day, when a task has ended_at within this day
        # it should not return a boefje task
        self.mock_ctx.config.pq_populate_grace_period = 86400

        tasks = self.scheduler.create_tasks_for_oois([ooi])
        self.assertEqual(0, len(tasks))

    @mock.patch("scheduler.context.AppContext.services.bytes.get_last_run_boefje")
    @mock.patch("scheduler.context.AppContext.services.katalogus.get_boefjes_by_type_and_org_id")
    def test_create_tasks_for_oois_grace_period_passed(
        self, mock_get_boefjes_by_type_and_org_id, mock_get_last_run_boefje
    ):
        """When a boefje has been run recently, when the grace period has passed
        it should return a boefje task
        """
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefjes = [PluginFactory(type="boefje", scan_level=0)]
        last_run_boefje = BoefjeMetaFactory(
            boefje=boefjes[0],
            input_ooi=ooi.primary_key,
            ended_at=datetime.now(timezone.utc) - timedelta(days=1),
        )

        mock_get_boefjes_by_type_and_org_id.return_value = boefjes
        mock_get_last_run_boefje.return_value = last_run_boefje

        # Set grace period for a day, when a task has ended_at after this day
        # it should not return a boefje task
        self.mock_ctx.config.pq_populate_grace_period = 86400

        tasks = self.scheduler.create_tasks_for_oois([ooi])
        self.assertEqual(1, len(tasks))

    @mock.patch("scheduler.context.AppContext.services.bytes.get_last_run_boefje")
    @mock.patch("scheduler.context.AppContext.services.katalogus.get_boefjes_by_type_and_org_id")
    def test_create_tasks_for_oois_boefje_still_running(
        self, mock_get_boefjes_by_type_and_org_id, mock_get_last_run_boefje
    ):
        """When a boefje is still running, it should not return a boefje task"""
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefjes = [PluginFactory(type="boefje", scan_level=0)]
        last_run_boefje = BoefjeMetaFactory(
            boefje=boefjes[0],
            input_ooi=ooi.primary_key,
            ended_at=None,
            started_at=datetime.now(timezone.utc),
        )

        mock_get_boefjes_by_type_and_org_id.return_value = boefjes
        mock_get_last_run_boefje.return_value = last_run_boefje

        tasks = self.scheduler.create_tasks_for_oois([ooi])
        self.assertEqual(0, len(tasks))

    @mock.patch("scheduler.context.AppContext.services.katalogus.get_boefjes_by_type_and_org_id")
    def test_populate_boefjes_queue_qsize(self, mock_get_boefjes_by_type_and_org_id):
        """When the boefje queue is full, it should not return a boefje task"""
        organisation = OrganisationFactory()

        # Make a queue with only one open slot
        queue = queues.BoefjePriorityQueue(
            pq_id=organisation.id,
            maxsize=1,
            item_type=models.BoefjeTask,
            allow_priority_updates=True,
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
        queue.push(queues.PrioritizedItem(0, task))

        self.scheduler.queue = queue

        self.assertEqual(1, self.scheduler.queue.qsize())
        self.scheduler.populate_queue()
        self.assertEqual(1, self.scheduler.queue.qsize())

    @mock.patch("scheduler.context.AppContext.services.scan_profile.get_latest_object")
    @mock.patch("scheduler.context.AppContext.services.octopoes.get_random_objects")
    @mock.patch("scheduler.schedulers.BoefjeScheduler.create_tasks_for_oois")
    def test_post_push(self, mock_create_tasks_for_oois, mock_get_random_objects, mock_get_latest_object):
        """When a task is added to the queue, it should be added to the database"""
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        task = models.BoefjeTask(
            id=uuid.uuid4().hex,
            boefje=BoefjeFactory(),
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        mock_get_latest_object.side_effect = [ooi, None]
        mock_get_random_objects.return_value = []
        mock_create_tasks_for_oois.side_effect = [
            [
                queues.PrioritizedItem(
                    priority=0,
                    item=task,
                )
            ],
        ]

        self.scheduler.populate_queue()
        self.assertEqual(1, self.scheduler.queue.qsize())
        self.assertEqual(task, self.scheduler.queue.peek(0).p_item.item)

        task_db = self.mock_ctx.datastore.get_task_by_id(task.id)
        self.assertEqual(task_db.id.hex, task.id)
        self.assertEqual(task_db.status, models.TaskStatus.QUEUED)

    @mock.patch("scheduler.context.AppContext.services.scan_profile.get_latest_object")
    @mock.patch("scheduler.context.AppContext.services.octopoes.get_random_objects")
    @mock.patch("scheduler.schedulers.BoefjeScheduler.create_tasks_for_oois")
    def test_post_pop(self, mock_create_tasks_for_oois, mock_get_random_objects, mock_get_latest_object):
        """When a task is removed from the queue, its status should be updated"""
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        task = models.BoefjeTask(
            id=uuid.uuid4().hex,
            boefje=BoefjeFactory(),
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        mock_get_latest_object.side_effect = [ooi, None]
        mock_get_random_objects.return_value = []
        mock_create_tasks_for_oois.side_effect = [
            [
                queues.PrioritizedItem(
                    priority=0,
                    item=task,
                )
            ],
        ]

        self.scheduler.populate_queue()
        self.assertEqual(1, self.scheduler.queue.qsize())
        self.assertEqual(task, self.scheduler.queue.peek(0).p_item.item)

        task_db = self.mock_ctx.datastore.get_task_by_id(task.id)
        self.assertEqual(task_db.id.hex, task.id)
