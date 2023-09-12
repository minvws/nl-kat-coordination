import json
import unittest
from types import SimpleNamespace
from unittest import mock

from scheduler import config, models, storage
from scheduler.storage import filters
from sqlalchemy import select

from tests.factories import OrganisationFactory
from tests.mocks import queue as mock_queue
from tests.mocks import scheduler as mock_scheduler
from tests.utils import functions


class FilterTestCase(unittest.TestCase):
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

        # Organisation
        self.organisation = OrganisationFactory()

        # Queue and Scheduler
        queue = mock_queue.MockPriorityQueue(
            pq_id=self.organisation.id,
            maxsize=10,
            item_type=functions.TestModel,
            allow_priority_updates=True,
            pq_store=self.mock_ctx.datastores.pq_store,
        )

        self.scheduler = mock_scheduler.MockScheduler(
            ctx=self.mock_ctx,
            scheduler_id=self.organisation.id,
            queue=queue,
        )

    def tearDown(self):
        self.dbconn.engine.dispose()

    def test_filter(self):
        # Add tasks
        p_item = functions.create_p_item(self.organisation.id, 0)
        task = functions.create_task(p_item)
        self.mock_ctx.datastores.task_store.create_task(task)

        values = json.dumps({"id": p_item.data.get("id")})

        with self.dbconn.session.begin() as session:
            # sqlalchemy.sql.elements.BinaryExpression
            expression = models.TaskDB.p_item["data"]

            # sqlalchemy 2.0
            # sqlalchemy.sql.selectable.Select
            query1 = select(models.TaskDB)\
                .where(
                    expression.op('@>')(values)
                )

            # sqlalchemy.orm.query.Query
            query2 = session.query(models.TaskDB)\
                .filter(
                    expression.op('@>')(values)
                )

            print(session.execute(query1).all())
            print(query2.all())
            breakpoint()

    def test_apply_filter(self):
        # Add tasks
        p_item = functions.create_p_item(self.organisation.id, 0)
        task = functions.create_task(p_item)
        self.mock_ctx.datastores.task_store.create_task(task)

        values = json.dumps({"id": p_item.data.get("id")})
        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="p_item",
                    field="data",
                    operator="@>",
                    value=values,
                )
            ],
        )

        with self.dbconn.session.begin() as session:
            query = session.query(models.TaskDB)
            query = filters.apply_filter(models.TaskDB, query, f_req)
            print(query.all())

        values = p_item.data.get("id")
        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="p_item",
                    field="data__id",
                    operator="==",
                    value=values,
                )
            ],
        )

        with self.dbconn.session.begin() as session:
            query = session.query(models.TaskDB)
            query = filters.apply_filter(models.TaskDB, query, f_req)
            print(query.all())
            breakpoint()
