import datetime
import json
import unittest
import uuid
from unittest import mock

from scheduler import config, connectors, models, queues, rankers, schedulers
from tests.factories import (
    BoefjeMetaFactory,
    OOIFactory,
    OrganisationFactory,
    PluginFactory,
    RawDataFactory,
    ScanProfileFactory,
)


class NormalizerSchedulerTestCase(unittest.TestCase):
    def setUp(self):
        cfg = config.settings.Settings()

        self.mock_ctx = mock.patch("scheduler.context.AppContext").start()
        self.mock_ctx.config = cfg

        # Scheduler
        self.organisation = OrganisationFactory()

        queue = queues.NormalizerPriorityQueue(
            pq_id=f"normalizer-{self.organisation.id}",
            maxsize=cfg.pq_maxsize,
            item_type=models.NormalizerTask,
            allow_priority_updates=True,
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
        boefje_meta = BoefjeMetaFactory(
            boefje=boefje,
            input_ooi=ooi.primary_key,
        )

        latest_raw_data = models.RawDataReceivedEvent(
            raw_data=RawDataFactory(boefje_meta=boefje_meta),
            organization=self.organisation.name,
            created_at=datetime.datetime.now(),
        )

        task = models.NormalizerTask(
            id=uuid.uuid4().hex,
            normalizer=PluginFactory(type="normalizer"),
            boefje_meta=boefje_meta,
        )

        mock_get_latest_raw_data.side_effect = [latest_raw_data, None]
        mock_get_normalizers.return_value = []
        mock_create_tasks_for_raw_data.side_effect = [
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
        boefje_meta = BoefjeMetaFactory(
            boefje=boefje,
            input_ooi=ooi.primary_key,
        )

        p_item = models.QueuePrioritizedItem(
            priority=1,
            item=models.BoefjeTask(
                boefje=boefje,
                input_ooi=ooi.primary_key,
                organization=self.organisation.id,
            ),
        )

        task = models.Task(
            id=p_item.item.id,
            hash=p_item.item.hash,
            scheduler_id=self.scheduler.scheduler_id,
            task=models.QueuePrioritizedItem(**p_item.dict()),
            status=models.TaskStatus.DISPATCHED,
            created_at=datetime.datetime.now(),
            modified_at=datetime.datetime.now(),
        )

        latest_raw_data = models.RawDataReceivedEvent(
            raw_data=RawDataFactory(
                boefje_meta=boefje_meta, mime_types=[{"value": "error/boefje"}, {"value": "text/xml"}]
            ),
            organization=self.organisation.name,
            created_at=datetime.datetime.now(),
        )

        mock_get_latest_raw_data.side_effect = [latest_raw_data, None]
        mock_get_normalizers.return_value = []

        self.scheduler.populate_queue()

        self.assertEqual(0, self.scheduler.queue.qsize())
        task_db_updated = self.mock_ctx.datastore.get_task_by_id(task.id)
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
        boefje_meta = BoefjeMetaFactory(
            boefje=boefje,
            input_ooi=ooi.primary_key,
        )

        p_item = models.QueuePrioritizedItem(
            priority=1,
            item=models.BoefjeTask(
                boefje=boefje,
                input_ooi=ooi.primary_key,
                organization=self.organisation.id,
            ),
        )

        task = models.Task(
            id=p_item.item.id,
            hash=p_item.item.hash,
            scheduler_id=self.scheduler.scheduler_id,
            task=models.QueuePrioritizedItem(**p_item.dict()),
            status=models.TaskStatus.DISPATCHED,
            created_at=datetime.datetime.now(),
            modified_at=datetime.datetime.now(),
        )

        latest_raw_data = models.RawDataReceivedEvent(
            raw_data=RawDataFactory(boefje_meta=boefje_meta, mime_types=[{"value": "text/plain"}]),
            organization=self.organisation.name,
            created_at=datetime.datetime.now(),
        )

        mock_get_latest_raw_data.side_effect = [latest_raw_data, None]
        mock_get_normalizers.return_value = []

        self.scheduler.populate_queue()

        self.assertEqual(0, self.scheduler.queue.qsize())
        task_db_updated = self.mock_ctx.datastore.get_task_by_id(task.id)
        self.assertEqual(task_db_updated.status, models.TaskStatus.COMPLETED)

    # TODO
    def test_update_normalizer_task(self):
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
