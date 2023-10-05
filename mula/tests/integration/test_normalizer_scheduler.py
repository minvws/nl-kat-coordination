import datetime
import unittest
from types import SimpleNamespace
from unittest import mock

import requests
from scheduler import config, models, schedulers, storage

from tests.factories import (
    BoefjeFactory,
    BoefjeMetaFactory,
    NormalizerFactory,
    OOIFactory,
    OrganisationFactory,
    PluginFactory,
    RawDataFactory,
    ScanProfileFactory,
)
from tests.utils import functions


class NormalizerSchedulerBaseTestCase(unittest.TestCase):
    def setUp(self):
        # Application Context
        self.mock_ctx = mock.patch("scheduler.context.AppContext").start()
        self.mock_ctx.config = config.settings.Settings()

        # Database
        self.dbconn = storage.DBConn(str(self.mock_ctx.config.db_uri))
        models.Base.metadata.create_all(self.dbconn.engine)
        self.mock_ctx.datastores = SimpleNamespace(
            **{
                storage.TaskStore.name: storage.TaskStore(self.dbconn),
                storage.PriorityQueueStore.name: storage.PriorityQueueStore(self.dbconn),
            }
        )

        # Scheduler
        self.organisation = OrganisationFactory()
        self.scheduler = schedulers.NormalizerScheduler(
            ctx=self.mock_ctx,
            scheduler_id=self.organisation.id,
            organisation=self.organisation,
        )

    def tearDown(self):
        self.scheduler.stop()
        models.Base.metadata.drop_all(self.dbconn.engine)
        self.dbconn.engine.dispose()


class NormalizerSchedulerTestCase(NormalizerSchedulerBaseTestCase):
    def setUp(self):
        super().setUp()

        self.mock_latest_task_by_hash = mock.patch(
            "scheduler.context.AppContext.datastores.task_store.get_latest_task_by_hash"
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
        tasks, _ = self.mock_ctx.datastores.task_store.get_tasks(self.scheduler.scheduler_id)
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
        tasks, _ = self.mock_ctx.datastores.task_store.get_tasks(self.scheduler.scheduler_id)
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

    def test_is_allowed_to_run(self):
        # Arrange
        normalizer = PluginFactory()

        # Act
        result = self.scheduler.is_task_allowed_to_run(normalizer)

        # Assert
        self.assertTrue(result)

    def test_is_not_allowed_to_run(self):
        # Arrange
        normalizer = PluginFactory()
        normalizer.enabled = False

        # Act
        result = self.scheduler.is_task_allowed_to_run(normalizer)

        # Assert
        self.assertFalse(result)

    @mock.patch("scheduler.context.AppContext.services.katalogus.get_normalizers_by_org_id_and_type")
    def test_get_normalizers_for_mime_type(self, mock_get_normalizers_by_org_id_and_type):
        # Arrange
        normalizer = NormalizerFactory()

        # Mocks
        mock_get_normalizers_by_org_id_and_type.return_value = [normalizer]

        # Act
        result = self.scheduler.get_normalizers_for_mime_type("text/plain")

        # Assert
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], normalizer)

    @mock.patch("scheduler.context.AppContext.services.katalogus.get_normalizers_by_org_id_and_type")
    def test_get_normalizers_for_mime_type_request_exception(self, mock_get_normalizers_by_org_id_and_type):
        # Mocks
        mock_get_normalizers_by_org_id_and_type.side_effect = [
            requests.exceptions.RetryError(),
            requests.exceptions.ConnectionError(),
        ]

        # Act
        result = self.scheduler.get_normalizers_for_mime_type("text/plain")

        # Assert
        self.assertEqual(len(result), 0)

    @mock.patch("scheduler.context.AppContext.services.katalogus.get_normalizers_by_org_id_and_type")
    def test_get_normalizers_for_mime_type_response_is_none(self, mock_get_normalizers_by_org_id_and_type):
        # Mocks
        mock_get_normalizers_by_org_id_and_type.return_value = None

        # Act
        result = self.scheduler.get_normalizers_for_mime_type("text/plain")

        # Assert
        self.assertEqual(len(result), 0)


class RawFileReceivedTestCase(NormalizerSchedulerBaseTestCase):
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

    def test_push_tasks_for_received_raw_file(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = BoefjeFactory()
        boefje_task = models.BoefjeTask(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        p_item = functions.create_p_item(scheduler_id=self.scheduler.scheduler_id, priority=1, data=boefje_task)
        task = functions.create_task(p_item)
        self.mock_ctx.datastores.task_store.create_task(task)

        boefje_meta = BoefjeMetaFactory(
            id=p_item.id,
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
            NormalizerFactory(),
        ]

        # Act
        self.scheduler.push_tasks_for_received_raw_data(raw_data_event)

        # Task should be on priority queue
        task_pq = models.NormalizerTask(**self.scheduler.queue.peek(0).data)
        self.assertEqual(1, self.scheduler.queue.qsize())

        # Task should be in datastore
        task_db = self.mock_ctx.datastores.task_store.get_task_by_id(task_pq.id)
        self.assertEqual(task_db.id, task_pq.id)
        self.assertEqual(task_db.status, models.TaskStatus.QUEUED)

    def test_push_tasks_for_received_raw_file_no_normalizers_found(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = BoefjeFactory()
        boefje_task = models.BoefjeTask(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        p_item = functions.create_p_item(scheduler_id=self.scheduler.scheduler_id, priority=1, data=boefje_task)
        task = functions.create_task(p_item)
        self.mock_ctx.datastores.task_store.create_task(task)

        boefje_meta = BoefjeMetaFactory(
            id=p_item.id,
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
        boefje = BoefjeFactory()
        boefje_task = models.BoefjeTask(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        p_item = functions.create_p_item(scheduler_id=self.scheduler.scheduler_id, priority=1, data=boefje_task)
        task = functions.create_task(p_item)
        self.mock_ctx.datastores.task_store.create_task(task)

        boefje_meta = BoefjeMetaFactory(
            id=p_item.id,
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

        self.mock_get_normalizers_for_mime_type.return_value = [
            NormalizerFactory(),
        ]
        self.mock_is_task_allowed_to_run.return_value = False

        # Act
        self.scheduler.push_tasks_for_received_raw_data(raw_data_event)

        # Task should not be on priority queue
        self.assertEqual(0, self.scheduler.queue.qsize())

    def test_push_tasks_for_received_raw_file_still_running(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = BoefjeFactory()
        boefje_task = models.BoefjeTask(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        p_item = functions.create_p_item(scheduler_id=self.scheduler.scheduler_id, priority=1, data=boefje_task)
        task = functions.create_task(p_item)
        self.mock_ctx.datastores.task_store.create_task(task)

        boefje_meta = BoefjeMetaFactory(
            id=p_item.id,
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

        self.mock_get_normalizers_for_mime_type.return_value = [
            NormalizerFactory(),
        ]
        self.mock_is_task_allowed_to_run.return_value = True
        self.mock_is_task_running.return_value = True

        # Act
        self.scheduler.push_tasks_for_received_raw_data(raw_data_event)

        # Task should not be on priority queue
        self.assertEqual(0, self.scheduler.queue.qsize())

    def test_push_tasks_for_received_raw_file_still_running_exception(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = BoefjeFactory()
        boefje_task = models.BoefjeTask(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        p_item = functions.create_p_item(scheduler_id=self.scheduler.scheduler_id, priority=1, data=boefje_task)
        task = functions.create_task(p_item)
        self.mock_ctx.datastores.task_store.create_task(task)

        boefje_meta = BoefjeMetaFactory(
            id=p_item.id,
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

        self.mock_get_normalizers_for_mime_type.return_value = [
            NormalizerFactory(),
        ]
        self.mock_is_task_allowed_to_run.return_value = True
        self.mock_is_task_running.side_effect = Exception("Something went wrong")

        # Act
        self.scheduler.push_tasks_for_received_raw_data(raw_data_event)

        # Task should not be on priority queue
        self.assertEqual(0, self.scheduler.queue.qsize())

    def test_push_tasks_for_received_raw_file_item_on_queue(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = BoefjeFactory()
        boefje_task = models.BoefjeTask(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        p_item = functions.create_p_item(scheduler_id=self.scheduler.scheduler_id, priority=1, data=boefje_task)
        task = functions.create_task(p_item)
        self.mock_ctx.datastores.task_store.create_task(task)

        boefje_meta = BoefjeMetaFactory(
            id=p_item.id,
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
            NormalizerFactory(),
        ]

        # Act
        self.scheduler.push_tasks_for_received_raw_data(raw_data_event1)
        self.scheduler.push_tasks_for_received_raw_data(raw_data_event2)

        # Task should be on priority queue (only one)
        task_pq = models.NormalizerTask(**self.scheduler.queue.peek(0).data)
        self.assertEqual(1, self.scheduler.queue.qsize())

        # Task should be in datastore
        task_db = self.mock_ctx.datastores.task_store.get_task_by_id(task_pq.id)
        self.assertEqual(task_db.id, task_pq.id)
        self.assertEqual(task_db.status, models.TaskStatus.QUEUED)

    def test_push_tasks_for_received_raw_file_error_mimetype(self):
        # Arrange
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = BoefjeFactory()
        boefje_task = models.BoefjeTask(
            boefje=boefje,
            input_ooi=ooi.primary_key,
            organization=self.organisation.id,
        )

        p_item = functions.create_p_item(scheduler_id=self.scheduler.scheduler_id, priority=1, data=boefje_task)
        task = functions.create_task(p_item)
        self.mock_ctx.datastores.task_store.create_task(task)

        boefje_meta = BoefjeMetaFactory(
            id=p_item.id,
            boefje=boefje,
            input_ooi=ooi.primary_key,
        )

        raw_data_event = models.RawDataReceivedEvent(
            raw_data=RawDataFactory(
                boefje_meta=boefje_meta,
                mime_types=[{"value": "error/unknown"}],
            ),
            organization=self.organisation.name,
            created_at=datetime.datetime.now(),
        )

        # Act
        self.scheduler.push_tasks_for_received_raw_data(raw_data_event)

        # Task should not be on priority queue
        self.assertEqual(0, self.scheduler.queue.qsize())

    def test_push_tasks_for_received_raw_file_queue_full(self):
        events = []
        for _ in range(0, 2):
            # Arrange
            scan_profile = ScanProfileFactory(level=0)
            ooi = OOIFactory(scan_profile=scan_profile)
            boefje = BoefjeFactory()
            boefje_task = models.BoefjeTask(
                boefje=boefje,
                input_ooi=ooi.primary_key,
                organization=self.organisation.id,
            )

            p_item = functions.create_p_item(scheduler_id=self.scheduler.scheduler_id, priority=1, data=boefje_task)
            task = functions.create_task(p_item)
            self.mock_ctx.datastores.task_store.create_task(task)

            boefje_meta = BoefjeMetaFactory(
                id=p_item.id,
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

            events.append(raw_data_event)

        self.scheduler.queue.maxsize = 1
        self.scheduler.max_tries = 1

        # Mocks
        self.mock_get_normalizers_for_mime_type.return_value = [
            NormalizerFactory(),
        ]

        # Act
        self.scheduler.push_tasks_for_received_raw_data(events[0])

        # Assert
        self.assertEqual(1, self.scheduler.queue.qsize())

        with self.assertLogs("scheduler.schedulers", level="DEBUG") as cm:
            self.scheduler.push_tasks_for_received_raw_data(events[1])

        self.assertIn("Could not add task to queue, queue was full", cm.output[-1])
        self.assertEqual(1, self.scheduler.queue.qsize())
