import datetime
import unittest
from unittest import mock

from scheduler import config, models, queues, repositories, schedulers

from tests.factories import (
    BoefjeMetaFactory,
    OOIFactory,
    OrganisationFactory,
    PluginFactory,
    RawDataFactory,
    ScanProfileFactory,
)
from tests.utils import functions


class NormalizerSchedulerBaseTestCase(unittest.TestCase):
    def setUp(self):
        cfg = config.settings.Settings()

        self.mock_ctx = mock.patch("scheduler.context.AppContext").start()
        self.mock_ctx.config = cfg

        # Datastore
        self.mock_ctx.datastore = repositories.sqlalchemy.SQLAlchemy(cfg.database_dsn)

        models.Base.metadata.create_all(self.mock_ctx.datastore.engine)
        self.pq_store = repositories.sqlalchemy.PriorityQueueStore(self.mock_ctx.datastore)
        self.task_store = repositories.sqlalchemy.TaskStore(self.mock_ctx.datastore)

        self.mock_ctx.pq_store = self.pq_store
        self.mock_ctx.task_store = self.task_store

        # Scheduler
        self.organisation = OrganisationFactory()

        queue = queues.NormalizerPriorityQueue(
            pq_id=self.organisation.id,
            maxsize=cfg.pq_maxsize,
            item_type=models.NormalizerTask,
            allow_priority_updates=True,
            pq_store=self.pq_store,
        )

        self.scheduler = schedulers.NormalizerScheduler(
            ctx=self.mock_ctx,
            scheduler_id=self.organisation.id,
            queue=queue,
            organisation=self.organisation,
        )


class NormalizerSchedulerTestCase(NormalizerSchedulerBaseTestCase):
    def setUp(self):
        super().setUp()

        self.mock_is_task_running = mock.patch(
            "scheduler.schedulers.NormalizerScheduler.is_task_running",
            return_value=False,
        ).start()

        self.mock_is_task_allowed_to_run = mock.patch(
            "scheduler.schedulers.NormalizerScheduler.is_task_allowed_to_run",
            return_value=True,
        ).start()

        self.mock_get_normalizers_for_mime_type = mock.patch(
            "scheduler.schedulers.NormalizerScheduler.get_normalizers_for_mime_type"
        ).start()

    def test_disable_scheduler(self):
        # Act
        self.scheduler.disable()

        # Listeners should be stopped
        self.assertEqual(0, len(self.scheduler.listeners))

        # Threads should be stopped
        self.assertEqual(0, len(self.scheduler.threads))

        # Queue should be empty
        self.assertEqual(0, self.scheduler.queue.qsize())

        # All tasks on queue should be set to CANCELLED
        tasks, _ = self.mock_ctx.task_store.get_tasks(self.scheduler.scheduler_id)
        for task in tasks:
            self.assertEqual(task.status, models.TaskStatus.CANCELLED)

        # Scheduler should be disabled
        self.assertFalse(self.scheduler.is_enabled())

    def test_enable_scheduler(self):
        # Disable scheduler first
        self.scheduler.disable()

        # Listeners should be stopped
        self.assertEqual(0, len(self.scheduler.listeners))

        # Threads should be stopped
        self.assertEqual(0, len(self.scheduler.threads))

        # Queue should be empty
        self.assertEqual(0, self.scheduler.queue.qsize())

        # All tasks on queue should be set to CANCELLED
        tasks, _ = self.mock_ctx.task_store.get_tasks(self.scheduler.scheduler_id)
        for task in tasks:
            self.assertEqual(task.status, models.TaskStatus.CANCELLED)

        # Re-enable scheduler
        self.scheduler.enable()

        # Threads should be started
        self.assertGreater(len(self.scheduler.threads), 0)

        # Scheduler should be enabled
        self.assertTrue(self.scheduler.is_enabled())

        # Stop the scheduler
        self.scheduler.stop()

    def test_push_tasks_for_received_raw_file(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(type="boefje", scan_level=0)
        boefje_task = models.BoefjeTask(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        p_item = functions.create_p_item(scheduler_id=self.scheduler.scheduler_id, priority=1, data=boefje_task)
        task = functions.create_task(p_item)
        self.mock_ctx.task_store.create_task(task)

        boefje_meta = BoefjeMetaFactory(
            id=p_item.id.hex,
            boefje=boefje,
            input_ooi=ooi.primary_key,
        )

        raw_data_event = models.RawDataReceivedEvent(
            raw_data=RawDataFactory(
                boefje_meta=boefje_meta,
                mime_types=[{"value": "text/plain"}],
            ),
            organization=self.organisation.name,
            created_at=datetime.datetime.now(),
        )

        # Mocks
        self.mock_get_normalizers_for_mime_type.return_value = [
            PluginFactory(type="normalizer"),
        ]

        # Act
        self.scheduler.push_tasks_for_received_raw_data(raw_data_event)

        # Task should be on priority queue
        task_pq = models.NormalizerTask(**self.scheduler.queue.peek(0).data)
        self.assertEqual(1, self.scheduler.queue.qsize())

        # Task should be in datastore
        task_db = self.mock_ctx.task_store.get_task_by_id(task_pq.id)
        self.assertEqual(task_db.id.hex, task_pq.id)
        self.assertEqual(task_db.status, models.TaskStatus.QUEUED)

    def test_push_tasks_for_received_raw_file_no_normalizers_found(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(type="boefje", scan_level=0)
        boefje_task = models.BoefjeTask(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        p_item = functions.create_p_item(scheduler_id=self.scheduler.scheduler_id, priority=1, data=boefje_task)
        task = functions.create_task(p_item)
        self.mock_ctx.task_store.create_task(task)

        boefje_meta = BoefjeMetaFactory(
            id=p_item.id.hex,
            boefje=boefje,
            input_ooi=ooi.primary_key,
        )

        raw_data_event = models.RawDataReceivedEvent(
            raw_data=RawDataFactory(
                boefje_meta=boefje_meta,
                mime_types=[{"value": "text/plain"}],
            ),
            organization=self.organisation.name,
            created_at=datetime.datetime.now(),
        )

        # Mocks
        self.mock_get_normalizers_for_mime_type.return_value = []

        # Act
        self.scheduler.push_tasks_for_received_raw_data(raw_data_event)

        # Task should not be on priority queue
        self.assertEqual(0, self.scheduler.queue.qsize())

    def test_push_tasks_for_received_raw_file_not_allowed_to_run(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(type="boefje", scan_level=0)
        boefje_task = models.BoefjeTask(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        p_item = functions.create_p_item(scheduler_id=self.scheduler.scheduler_id, priority=1, data=boefje_task)
        task = functions.create_task(p_item)
        self.mock_ctx.task_store.create_task(task)

        boefje_meta = BoefjeMetaFactory(
            id=p_item.id.hex,
            boefje=boefje,
            input_ooi=ooi.primary_key,
        )

        # Mocks
        raw_data_event = models.RawDataReceivedEvent(
            raw_data=RawDataFactory(
                boefje_meta=boefje_meta,
                mime_types=[{"value": "text/plain"}],
            ),
            organization=self.organisation.name,
            created_at=datetime.datetime.now(),
        )

        self.mock_get_normalizers_for_mime_type.return_value = []
        self.mock_is_task_allowed_to_run.return_value = False

        # Act
        self.scheduler.push_tasks_for_received_raw_data(raw_data_event)

        # Task should not be on priority queue
        self.assertEqual(0, self.scheduler.queue.qsize())

    def test_push_tasks_for_received_raw_file_still_running(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(type="boefje", scan_level=0)
        boefje_task = models.BoefjeTask(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        p_item = functions.create_p_item(scheduler_id=self.scheduler.scheduler_id, priority=1, data=boefje_task)
        task = functions.create_task(p_item)
        self.mock_ctx.task_store.create_task(task)

        boefje_meta = BoefjeMetaFactory(
            id=p_item.id.hex,
            boefje=boefje,
            input_ooi=ooi.primary_key,
        )

        # Mocks
        raw_data_event = models.RawDataReceivedEvent(
            raw_data=RawDataFactory(
                boefje_meta=boefje_meta,
                mime_types=[{"value": "text/plain"}],
            ),
            organization=self.organisation.name,
            created_at=datetime.datetime.now(),
        )

        self.mock_get_normalizers_for_mime_type.return_value = []
        self.mock_is_task_running.return_value = False

        # Act
        self.scheduler.push_tasks_for_received_raw_data(raw_data_event)

        # Task should not be on priority queue
        self.assertEqual(0, self.scheduler.queue.qsize())

    def test_push_tasks_for_received_raw_file_item_on_queue(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(type="boefje", scan_level=0)
        boefje_task = models.BoefjeTask(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        p_item = functions.create_p_item(scheduler_id=self.scheduler.scheduler_id, priority=1, data=boefje_task)
        task = functions.create_task(p_item)
        self.mock_ctx.task_store.create_task(task)

        boefje_meta = BoefjeMetaFactory(
            id=p_item.id.hex,
            boefje=boefje,
            input_ooi=ooi.primary_key,
        )

        # Mocks
        raw_data_event1 = models.RawDataReceivedEvent(
            raw_data=RawDataFactory(
                boefje_meta=boefje_meta,
                mime_types=[{"value": "text/plain"}],
            ),
            organization=self.organisation.name,
            created_at=datetime.datetime.now(),
        )

        raw_data_event2 = models.RawDataReceivedEvent(
            raw_data=RawDataFactory(
                boefje_meta=boefje_meta,
                mime_types=[{"value": "text/plain"}],
            ),
            organization=self.organisation.name,
            created_at=datetime.datetime.now(),
        )

        self.mock_get_normalizers_for_mime_type.return_value = [
            PluginFactory(type="normalizer"),
        ]

        # Act
        self.scheduler.push_tasks_for_received_raw_data(raw_data_event1)
        self.scheduler.push_tasks_for_received_raw_data(raw_data_event2)

        # Task should be on priority queue (only one)
        task_pq = models.NormalizerTask(**self.scheduler.queue.peek(0).data)
        self.assertEqual(1, self.scheduler.queue.qsize())

        # Task should be in datastore
        task_db = self.mock_ctx.task_store.get_task_by_id(task_pq.id)
        self.assertEqual(task_db.id.hex, task_pq.id)
        self.assertEqual(task_db.status, models.TaskStatus.QUEUED)

    def test_push_tasks_for_received_raw_file_error_mimetype(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(type="boefje", scan_level=0)
        boefje_task = models.BoefjeTask(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        p_item = functions.create_p_item(scheduler_id=self.scheduler.scheduler_id, priority=1, data=boefje_task)
        task = functions.create_task(p_item)
        self.mock_ctx.task_store.create_task(task)

        boefje_meta = BoefjeMetaFactory(
            id=p_item.id.hex,
            boefje=boefje,
            input_ooi=ooi.primary_key,
        )

        raw_data_event = models.RawDataReceivedEvent(
            raw_data=RawDataFactory(
                boefje_meta=boefje_meta,
                mime_types=[{"value": "text/plain"}],
            ),
            organization=self.organisation.name,
            created_at=datetime.datetime.now(),
        )

        # Act
        self.scheduler.push_tasks_for_received_raw_data(raw_data_event)

        # Task should not be on priority queue
        self.assertEqual(0, self.scheduler.queue.qsize())
