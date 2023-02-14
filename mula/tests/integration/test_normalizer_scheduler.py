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

    @mock.patch("scheduler.context.AppContext.services.raw_data.get_latest_raw_data")
    @mock.patch("scheduler.context.AppContext.services.katalogus.get_normalizers_by_org_id_and_type")
    @mock.patch("scheduler.schedulers.NormalizerScheduler.create_tasks_for_raw_data")
    def test_populate_normalizer_queue_get_latest_raw_data(
        self, mock_create_tasks_for_raw_data, mock_get_normalizers, mock_get_latest_raw_data
    ):
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

        latest_raw_data = models.RawDataReceivedEvent(
            raw_data=RawDataFactory(boefje_meta=boefje_meta, mime_types=[{"value": "text/plain"}]),
            organization=self.organisation.name,
            created_at=datetime.datetime.now(),
        )

        normalizer_task = models.NormalizerTask(
            normalizer=PluginFactory(type="normalizer"),
            raw_data=RawDataFactory(boefje_meta=boefje_meta, mime_types=[{"value": "text/xml"}]),
        )

        p_item_normalizer = functions.create_p_item(
            scheduler_id=self.scheduler.scheduler_id, priority=1, data=normalizer_task
        )

        mock_get_latest_raw_data.side_effect = [latest_raw_data, None]
        mock_get_normalizers.return_value = []
        mock_create_tasks_for_raw_data.side_effect = [
            [p_item_normalizer],
        ]

        self.scheduler.populate_queue()

        self.assertEqual(1, self.scheduler.queue.qsize())
        self.assertEqual(p_item_normalizer.id, self.scheduler.queue.peek(0).id)

    @mock.patch("scheduler.context.AppContext.services.raw_data.get_latest_raw_data")
    def test_populate_normalizer_queue_no_raw_data(self, mock_get_latest_raw_data):
        mock_get_latest_raw_data.return_value = None

        self.scheduler.populate_queue()
        self.assertEqual(0, self.scheduler.queue.qsize())

    @mock.patch("scheduler.context.AppContext.services.raw_data.get_latest_raw_data")
    @mock.patch("scheduler.context.AppContext.services.katalogus.get_normalizers_by_org_id_and_type")
    def test_populate_normalizer_queue_update_boefje_status_failed(
        self, mock_get_normalizers, mock_get_latest_raw_data
    ):
        """When a boefje failed the boefje task status should be updated,
        and no task should be created because the mime_type contains "error/"
        """
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

        latest_raw_data = models.RawDataReceivedEvent(
            raw_data=RawDataFactory(
                boefje_meta=BoefjeMetaFactory(
                    id=p_item.id.hex,
                    boefje=boefje,
                    input_ooi=ooi.primary_key,
                ),
                mime_types=[{"value": "error/boefje"}, {"value": "text/xml"}],
            ),
            organization=self.organisation.name,
            created_at=datetime.datetime.now(),
        )

        mock_get_latest_raw_data.side_effect = [latest_raw_data, None]
        mock_get_normalizers.return_value = []

        self.scheduler.populate_queue()

        self.assertEqual(0, self.scheduler.queue.qsize())
        task_db_updated = self.mock_ctx.task_store.get_task_by_id(p_item.id)
        self.assertEqual(task_db_updated.status, models.TaskStatus.FAILED)

    @mock.patch("scheduler.context.AppContext.services.raw_data.get_latest_raw_data")
    @mock.patch("scheduler.context.AppContext.services.katalogus.get_normalizers_by_org_id_and_type")
    def test_populate_normalizer_queue_update_boefje_status_completed(
        self, mock_get_normalizers, mock_get_latest_raw_data
    ):
        """When a boefje suceeds the boefje task status should be updated
        to completed.
        """
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

        latest_raw_data = models.RawDataReceivedEvent(
            raw_data=RawDataFactory(
                boefje_meta=BoefjeMetaFactory(
                    id=p_item.id.hex,
                    boefje=boefje,
                    input_ooi=ooi.primary_key,
                ),
                mime_types=[{"value": "text/plain"}],
            ),
            organization=self.organisation.name,
            created_at=datetime.datetime.now(),
        )

        mock_get_latest_raw_data.side_effect = [latest_raw_data, None]
        mock_get_normalizers.return_value = []

        self.scheduler.populate_queue()

        self.assertEqual(0, self.scheduler.queue.qsize())
        task_db_updated = self.mock_ctx.task_store.get_task_by_id(p_item.id)
        self.assertEqual(task_db_updated.status, models.TaskStatus.COMPLETED)

    # TODO
    def test_update_normalizer_task(self):
        pass

    # TODO: when boefje task isnt available, but it should make a normalizers
    # task
    def test_populate_normalizer_queue_boefje_task_not_available(self):
        pass

    @mock.patch("scheduler.context.AppContext.services.raw_data.get_latest_raw_data")
    @mock.patch("scheduler.context.AppContext.services.katalogus.get_normalizers_by_org_id_and_type")
    def test_create_tasks_for_raw(self, mock_get_normalizers, mock_get_latest_raw_data):
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(type="boefje", scan_level=0)
        boefje_meta = BoefjeMetaFactory(
            boefje=boefje,
            input_ooi=ooi.primary_key,
        )

        normalizers = [PluginFactory(type="normalizer", scan_level=0) for _ in range(3)]

        raw_data = RawDataFactory(
            boefje_meta=boefje_meta,
        )

        mock_get_latest_raw_data.return_value = raw_data
        mock_get_normalizers.return_value = normalizers

        tasks = self.scheduler.create_tasks_for_raw_data(raw_data)
        self.assertGreaterEqual(len(tasks), 1)

    @mock.patch("scheduler.context.AppContext.services.raw_data.get_latest_raw_data")
    @mock.patch("scheduler.context.AppContext.services.katalogus.get_normalizers_by_org_id_and_type")
    def test_create_tasks_for_raw_normalizers_not_found(self, mock_get_normalizers, mock_get_latest_raw_data):
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(type="boefje", scan_level=0)
        boefje_meta = BoefjeMetaFactory(
            boefje=boefje,
            input_ooi=ooi.primary_key,
        )

        raw_data = RawDataFactory(
            boefje_meta=boefje_meta,
        )

        mock_get_latest_raw_data.return_value = raw_data
        mock_get_normalizers.return_value = []

        tasks = self.scheduler.create_tasks_for_raw_data(raw_data)
        self.assertGreaterEqual(0, len(tasks))

    @mock.patch("scheduler.context.AppContext.services.raw_data.get_latest_raw_data")
    @mock.patch("scheduler.context.AppContext.services.katalogus.get_normalizers_by_org_id_and_type")
    def test_create_task_for_raw_plugin_disabled(self, mock_get_normalizers, mock_get_latest_raw_data):
        scan_profile = ScanProfileFactory(level=0)
        ooi = OOIFactory(scan_profile=scan_profile)
        boefje = PluginFactory(type="boefje", scan_level=0)
        boefje_meta = BoefjeMetaFactory(
            boefje=boefje,
            input_ooi=ooi.primary_key,
        )

        normalizer = PluginFactory(type="normalizer", scan_level=0, enabled=False)

        raw_data = RawDataFactory(
            boefje_meta=boefje_meta,
        )

        mock_get_latest_raw_data.return_value = raw_data
        mock_get_normalizers.return_value = [normalizer]

        tasks = self.scheduler.create_tasks_for_raw_data(raw_data)
        self.assertEqual(0, len(tasks))
