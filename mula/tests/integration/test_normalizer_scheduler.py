import datetime
import unittest
from unittest import mock

from scheduler import config, models, queues, rankers, repositories, schedulers

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
        self.mock_ctx.datastore = repositories.sqlalchemy.SQLAlchemy("sqlite:///")

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

        ranker = rankers.NormalizerRanker(
            ctx=self.mock_ctx,
        )

        self.scheduler = schedulers.NormalizerScheduler(
            ctx=self.mock_ctx,
            scheduler_id=self.organisation.id,
            queue=queue,
            ranker=ranker,
            organisation=self.organisation,
        )


@mock.patch("scheduler.schedulers.NormalizerScheduler.is_task_running")  # index: 2
@mock.patch("scheduler.schedulers.NormalizerScheduler.is_task_allowed_to_run")  # index: 1
@mock.patch("scheduler.schedulers.NormalizerScheduler.get_normalizers_for_mime_type")  # index: 0
class NormalizerSchedulerTestCase(NormalizerSchedulerBaseTestCase):
    def test_push_tasks_for_received_raw_file(self, *mocks):
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
        mocks[0].return_value = [
            PluginFactory(type="normalizer"),
        ]
        mocks[1].return_value = True
        mocks[2].return_value = False

        # Act
        self.scheduler.push_tasks_for_received_raw_data(raw_data_event)

        # Task should be on priority queue
        task_pq = models.NormalizerTask(**self.scheduler.queue.peek(0).data)
        self.assertEqual(1, self.scheduler.queue.qsize())

        # Task should be in datastore
        task_db = self.mock_ctx.task_store.get_task_by_id(task_pq.id)
        self.assertEqual(task_db.id.hex, task_pq.id)
        self.assertEqual(task_db.status, models.TaskStatus.QUEUED)

    def test_push_tasks_for_received_raw_file_no_normalizers_found(self, *mocks):
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
        mocks[0].return_value = []
        mocks[1].return_value = True
        mocks[2].return_value = False

        # Act
        self.scheduler.push_tasks_for_received_raw_data(raw_data_event)

        # Task should not be on priority queue
        self.assertEqual(0, self.scheduler.queue.qsize())

    def test_push_tasks_for_received_raw_file_not_allowed_to_run(self, *mocks):
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

        mocks[0].return_value = []
        mocks[1].return_value = False
        mocks[2].return_value = False

        # Act
        self.scheduler.push_tasks_for_received_raw_data(raw_data_event)

        # Task should not be on priority queue
        self.assertEqual(0, self.scheduler.queue.qsize())

    def test_push_tasks_for_received_raw_file_still_running(self, *mocks):
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

        mocks[0].return_value = []
        mocks[1].return_value = True
        mocks[2].return_value = True

        # Act
        self.scheduler.push_tasks_for_received_raw_data(raw_data_event)

        # Task should not be on priority queue
        self.assertEqual(0, self.scheduler.queue.qsize())

    def test_push_tasks_for_received_raw_file_item_on_queue(self, *mocks):
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

        mocks[0].return_value = [
            PluginFactory(type="normalizer"),
        ]

        mocks[1].return_value = True
        mocks[2].return_value = False

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

    def test_push_tasks_for_received_raw_file_error_mimetype(self, *mocks):
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

        # Act
        self.scheduler.push_tasks_for_received_raw_data(raw_data_event)

        # Task should not be on priority queue
        self.assertEqual(0, self.scheduler.queue.qsize())

    def test_push_tasks_for_received_raw_file_queue_full(self, *mocks):
        self.fail("Not implemented")
