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


class NormalizerSchedulerTestCase(unittest.TestCase):
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

    @mock.patch("scheduler.schedulers.NormalizerScheduler.is_task_running")
    @mock.patch("scheduler.schedulers.NormalizerScheduler.is_task_allowed_to_run")
    @mock.patch("scheduler.schedulers.NormalizerScheduler.get_normalizers_for_mime_type")
    @mock.patch("scheduler.context.AppContext.services.raw_data.get_latest_raw_data")
    def test_push_tasks_for_received_raw_file(
        self,
        mock_get_latest_raw_data,
        mock_get_normalizers_for_mime_type,
        mock_is_task_allowed_to_run,
        mock_is_task_running,
    ):
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
        mock_get_latest_raw_data.side_effect = [
            models.RawDataReceivedEvent(
                raw_data=RawDataFactory(
                    boefje_meta=boefje_meta,
                    mime_types=[{"value": "text/plain"}],
                ),
                organization=self.organisation.name,
                created_at=datetime.datetime.now(),
            ),
            None,
        ]

        mock_get_normalizers_for_mime_type.return_value = [
            PluginFactory(type="normalizer"),
        ]
        mock_is_task_allowed_to_run.return_value = True
        mock_is_task_running.return_value = False

        # Act
        self.scheduler.push_tasks_for_received_raw_file()

        # Task should be on priority queue
        task_pq = models.NormalizerTask(**self.scheduler.queue.peek(0).data)
        self.assertEqual(1, self.scheduler.queue.qsize())

        # Task should be in datastore
        task_db = self.mock_ctx.task_store.get_task_by_id(task_pq.id)
        self.assertEqual(task_db.id.hex, task_pq.id)
        self.assertEqual(task_db.status, models.TaskStatus.QUEUED)

    @mock.patch("scheduler.schedulers.NormalizerScheduler.is_task_running")
    @mock.patch("scheduler.schedulers.NormalizerScheduler.is_task_allowed_to_run")
    @mock.patch("scheduler.schedulers.NormalizerScheduler.get_normalizers_for_mime_type")
    @mock.patch("scheduler.context.AppContext.services.raw_data.get_latest_raw_data")
    def test_push_tasks_for_received_raw_file_no_normalizers_found(
        self,
        mock_get_latest_raw_data,
        mock_get_normalizers_for_mime_type,
        mock_is_task_allowed_to_run,
        mock_is_task_running,
    ):
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
        mock_get_latest_raw_data.side_effect = [
            models.RawDataReceivedEvent(
                raw_data=RawDataFactory(
                    boefje_meta=boefje_meta,
                    mime_types=[{"value": "text/plain"}],
                ),
                organization=self.organisation.name,
                created_at=datetime.datetime.now(),
            ),
            None,
        ]

        mock_get_normalizers_for_mime_type.return_value = []
        mock_is_task_allowed_to_run.return_value = True
        mock_is_task_running.return_value = False

        # Act
        self.scheduler.push_tasks_for_received_raw_file()

        # Task should not be on priority queue
        self.assertEqual(0, self.scheduler.queue.qsize())

    @mock.patch("scheduler.schedulers.NormalizerScheduler.is_task_running")
    @mock.patch("scheduler.schedulers.NormalizerScheduler.is_task_allowed_to_run")
    @mock.patch("scheduler.schedulers.NormalizerScheduler.get_normalizers_for_mime_type")
    @mock.patch("scheduler.context.AppContext.services.raw_data.get_latest_raw_data")
    def test_push_tasks_for_received_raw_file_not_allowed_to_run(
        self,
        mock_get_latest_raw_data,
        mock_get_normalizers_for_mime_type,
        mock_is_task_allowed_to_run,
        mock_is_task_running,
    ):
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
        mock_get_latest_raw_data.side_effect = [
            models.RawDataReceivedEvent(
                raw_data=RawDataFactory(
                    boefje_meta=boefje_meta,
                    mime_types=[{"value": "text/plain"}],
                ),
                organization=self.organisation.name,
                created_at=datetime.datetime.now(),
            ),
            None,
        ]

        mock_get_normalizers_for_mime_type.return_value = []
        mock_is_task_allowed_to_run.return_value = False
        mock_is_task_running.return_value = False

        # Act
        self.scheduler.push_tasks_for_received_raw_file()

        # Task should not be on priority queue
        self.assertEqual(0, self.scheduler.queue.qsize())

    @mock.patch("scheduler.schedulers.NormalizerScheduler.is_task_running")
    @mock.patch("scheduler.schedulers.NormalizerScheduler.is_task_allowed_to_run")
    @mock.patch("scheduler.schedulers.NormalizerScheduler.get_normalizers_for_mime_type")
    @mock.patch("scheduler.context.AppContext.services.raw_data.get_latest_raw_data")
    def test_push_tasks_for_received_raw_file_still_running(
        self,
        mock_get_latest_raw_data,
        mock_get_normalizers_for_mime_type,
        mock_is_task_allowed_to_run,
        mock_is_task_running,
    ):
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
        mock_get_latest_raw_data.side_effect = [
            models.RawDataReceivedEvent(
                raw_data=RawDataFactory(
                    boefje_meta=boefje_meta,
                    mime_types=[{"value": "text/plain"}],
                ),
                organization=self.organisation.name,
                created_at=datetime.datetime.now(),
            ),
            None,
        ]

        mock_get_normalizers_for_mime_type.return_value = []
        mock_is_task_allowed_to_run.return_value = True
        mock_is_task_running.return_value = True

        # Act
        self.scheduler.push_tasks_for_received_raw_file()

        # Task should not be on priority queue
        self.assertEqual(0, self.scheduler.queue.qsize())

    @mock.patch("scheduler.schedulers.NormalizerScheduler.get_normalizers_for_mime_type")
    @mock.patch("scheduler.context.AppContext.services.raw_data.get_latest_raw_data")
    def test_push_tasks_for_received_raw_file_item_on_queue(
        self,
        mock_get_latest_raw_data,
        mock_get_normalizers_for_mime_type,
    ):
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
        mock_get_latest_raw_data.side_effect = [
            models.RawDataReceivedEvent(
                raw_data=RawDataFactory(
                    boefje_meta=boefje_meta,
                    mime_types=[{"value": "text/plain"}],
                ),
                organization=self.organisation.name,
                created_at=datetime.datetime.now(),
            ),
            models.RawDataReceivedEvent(
                raw_data=RawDataFactory(
                    boefje_meta=boefje_meta,
                    mime_types=[{"value": "text/plain"}],
                ),
                organization=self.organisation.name,
                created_at=datetime.datetime.now(),
            ),
            None,
        ]

        mock_get_normalizers_for_mime_type.return_value = [
            PluginFactory(type="normalizer"),
        ]

        # Act
        self.scheduler.push_tasks_for_received_raw_file()

        # Task should be on priority queue (only one)
        task_pq = models.NormalizerTask(**self.scheduler.queue.peek(0).data)
        self.assertEqual(1, self.scheduler.queue.qsize())

        # Task should be in datastore
        task_db = self.mock_ctx.task_store.get_task_by_id(task_pq.id)
        self.assertEqual(task_db.id.hex, task_pq.id)
        self.assertEqual(task_db.status, models.TaskStatus.QUEUED)

    @mock.patch("scheduler.context.AppContext.services.raw_data.get_latest_raw_data")
    def test_push_tasks_for_received_raw_file_error_mimetype(
        self,
        mock_get_latest_raw_data,
    ):
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
        mock_get_latest_raw_data.side_effect = [
            models.RawDataReceivedEvent(
                raw_data=RawDataFactory(
                    boefje_meta=boefje_meta,
                    mime_types=[{"value": "text/plain"}],
                ),
                organization=self.organisation.name,
                created_at=datetime.datetime.now(),
            ),
            None,
        ]

        # Act
        self.scheduler.push_tasks_for_received_raw_file()

        # Task should not be on priority queue
        self.assertEqual(0, self.scheduler.queue.qsize())
