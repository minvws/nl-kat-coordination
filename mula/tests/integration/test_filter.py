import json
import unittest
import uuid
from types import SimpleNamespace
from unittest import mock

from scheduler import config, models, storage
from scheduler.storage import filters
from sqlalchemy import select

from tests.factories import OrganisationFactory
from tests.utils import functions


def compile_query_postgres(query):
    from sqlalchemy.dialects import postgresql

    return str(query.statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))


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

    def tearDown(self):
        models.Base.metadata.drop_all(self.dbconn.engine)
        self.dbconn.engine.dispose()

    @unittest.skip("Not implemented")
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
            query1 = select(models.TaskDB).where(expression.op("@>")(values))

            # sqlalchemy.orm.query.Query
            query2 = session.query(models.TaskDB).filter(expression.op("@>")(values))

            print(session.execute(query1).all())
            print(query2.all())

    @unittest.skip("Not implemented")
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

        value_id = p_item.data.get("id")
        value_name = p_item.data.get("name")
        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="p_item",
                    field="data__id",
                    operator="==",
                    value=value_id,
                ),
                filters.Filter(
                    column="p_item",
                    field="data__name",
                    operator="==",
                    value=value_name,
                ),
            ],
        )

        with self.dbconn.session.begin() as session:
            query = session.query(models.TaskDB)
            query = filters.apply_filter(models.TaskDB, query, f_req)
            compiled_query = compile_query_postgres(query)
            print(compiled_query)
            breakpoint()

    def test_apply_filter_json_eq(self):
        # Arrange
        first_p_item = functions.create_p_item(self.organisation.id, 0)
        first_task = functions.create_task(first_p_item)
        self.mock_ctx.datastores.task_store.create_task(first_task)

        second_p_item = functions.create_p_item(self.organisation.id, 0)
        second_task = functions.create_task(second_p_item)
        self.mock_ctx.datastores.task_store.create_task(second_task)

        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="p_item",
                    field="data__id",
                    operator="eq",
                    value=first_p_item.data.get("id"),
                )
            ],
        )

        # Act
        with self.dbconn.session.begin() as session:
            query = session.query(models.TaskDB)
            query = filters.apply_filter(models.TaskDB, query, f_req)
            results = query.all()

            # Assert
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].p_item["data"]["id"], first_p_item.data.get("id"))

        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="p_item",
                    field="data__id",
                    operator="==",
                    value=first_p_item.data.get("id"),
                )
            ],
        )

        # Act
        with self.dbconn.session.begin() as session:
            query = session.query(models.TaskDB)
            query = filters.apply_filter(models.TaskDB, query, f_req)
            results = query.all()

            # Assert
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].p_item["data"]["id"], first_p_item.data.get("id"))

    def test_apply_filter_json_ne(self):
        # Arrange
        first_p_item = functions.create_p_item(self.organisation.id, 0)
        first_task = functions.create_task(first_p_item)
        self.mock_ctx.datastores.task_store.create_task(first_task)

        second_p_item = functions.create_p_item(self.organisation.id, 0)
        second_task = functions.create_task(second_p_item)
        self.mock_ctx.datastores.task_store.create_task(second_task)

        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="p_item",
                    field="data__id",
                    operator="ne",
                    value=first_p_item.data.get("id"),
                )
            ],
        )

        # Act
        with self.dbconn.session.begin() as session:
            query = session.query(models.TaskDB)
            query = filters.apply_filter(models.TaskDB, query, f_req)
            results = query.all()

            # Assert
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].p_item["data"]["id"], second_p_item.data.get("id"))

        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="p_item",
                    field="data__id",
                    operator="!=",
                    value=first_p_item.data.get("id"),
                )
            ],
        )

        # Act
        with self.dbconn.session.begin() as session:
            query = session.query(models.TaskDB)
            query = filters.apply_filter(models.TaskDB, query, f_req)
            results = query.all()

            # Assert
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].p_item["data"]["id"], second_p_item.data.get("id"))

    def test_apply_filter_json_is(self):
        pass

    def test_apply_filter_json_is_not(self):
        pass

    def test_apply_filter_json_gt(self):
        # Arrange
        first_p_item = functions.create_p_item(
            self.organisation.id, 0, functions.TestModel(id=uuid.uuid4().hex, name=uuid.uuid4().hex, count=1)
        )
        first_task = functions.create_task(first_p_item)
        self.mock_ctx.datastores.task_store.create_task(first_task)

        second_p_item = functions.create_p_item(
            self.organisation.id, 0, functions.TestModel(id=uuid.uuid4().hex, name=uuid.uuid4().hex, count=2)
        )
        second_task = functions.create_task(second_p_item)
        self.mock_ctx.datastores.task_store.create_task(second_task)

        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="p_item",
                    field="data__count",
                    operator="gt",
                    value=first_p_item.data.get("count"),
                )
            ],
        )

        # Act
        with self.dbconn.session.begin() as session:
            query = session.query(models.TaskDB)
            query = filters.apply_filter(models.TaskDB, query, f_req)
            results = query.all()

            # Assert
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].p_item["data"]["id"], second_p_item.data.get("id"))

        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="p_item",
                    field="data__count",
                    operator=">",
                    value=first_p_item.data.get("count"),
                )
            ],
        )

        # Act
        with self.dbconn.session.begin() as session:
            query = session.query(models.TaskDB)
            query = filters.apply_filter(models.TaskDB, query, f_req)
            results = query.all()

            # Assert
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].p_item["data"]["id"], second_p_item.data.get("id"))

    def test_apply_filter_json_gte(self):
        # Arrange
        first_p_item = functions.create_p_item(
            self.organisation.id, 0, functions.TestModel(id=uuid.uuid4().hex, name=uuid.uuid4().hex, count=1)
        )
        first_task = functions.create_task(first_p_item)
        self.mock_ctx.datastores.task_store.create_task(first_task)

        second_p_item = functions.create_p_item(
            self.organisation.id, 0, functions.TestModel(id=uuid.uuid4().hex, name=uuid.uuid4().hex, count=2)
        )
        second_task = functions.create_task(second_p_item)
        self.mock_ctx.datastores.task_store.create_task(second_task)

        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="p_item",
                    field="data__count",
                    operator="gte",
                    value=first_p_item.data.get("count"),
                )
            ],
        )

        # Act
        with self.dbconn.session.begin() as session:
            query = session.query(models.TaskDB)
            query = filters.apply_filter(models.TaskDB, query, f_req)
            results = query.all()

            # Assert
            self.assertEqual(len(results), 2)
            self.assertEqual(results[0].p_item["data"]["id"], first_p_item.data.get("id"))
            self.assertEqual(results[1].p_item["data"]["id"], second_p_item.data.get("id"))

        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="p_item",
                    field="data__count",
                    operator=">=",
                    value=first_p_item.data.get("count"),
                )
            ],
        )

        # Act
        with self.dbconn.session.begin() as session:
            query = session.query(models.TaskDB)
            query = filters.apply_filter(models.TaskDB, query, f_req)
            results = query.all()

            # Assert
            self.assertEqual(len(results), 2)
            self.assertEqual(results[0].p_item["data"]["id"], first_p_item.data.get("id"))
            self.assertEqual(results[1].p_item["data"]["id"], second_p_item.data.get("id"))

    def test_apply_filter_json_lt(self):
        # Arrange
        first_p_item = functions.create_p_item(
            self.organisation.id, 0, functions.TestModel(id=uuid.uuid4().hex, name=uuid.uuid4().hex, count=2)
        )
        first_task = functions.create_task(first_p_item)
        self.mock_ctx.datastores.task_store.create_task(first_task)

        second_p_item = functions.create_p_item(
            self.organisation.id, 0, functions.TestModel(id=uuid.uuid4().hex, name=uuid.uuid4().hex, count=1)
        )
        second_task = functions.create_task(second_p_item)
        self.mock_ctx.datastores.task_store.create_task(second_task)

        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="p_item",
                    field="data__count",
                    operator="lt",
                    value=first_p_item.data.get("count"),
                )
            ],
        )

        # Act
        with self.dbconn.session.begin() as session:
            query = session.query(models.TaskDB)
            query = filters.apply_filter(models.TaskDB, query, f_req)
            results = query.all()

            # Assert
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].p_item["data"]["id"], second_p_item.data.get("id"))

        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="p_item",
                    field="data__count",
                    operator="<",
                    value=first_p_item.data.get("count"),
                )
            ],
        )

        # Act
        with self.dbconn.session.begin() as session:
            query = session.query(models.TaskDB)
            query = filters.apply_filter(models.TaskDB, query, f_req)
            results = query.all()

            # Assert
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].p_item["data"]["id"], second_p_item.data.get("id"))

    def test_apply_filter_json_lte(self):
        # Arrange
        first_p_item = functions.create_p_item(
            self.organisation.id, 0, functions.TestModel(id=uuid.uuid4().hex, name=uuid.uuid4().hex, count=2)
        )
        first_task = functions.create_task(first_p_item)
        self.mock_ctx.datastores.task_store.create_task(first_task)

        second_p_item = functions.create_p_item(
            self.organisation.id, 0, functions.TestModel(id=uuid.uuid4().hex, name=uuid.uuid4().hex, count=1)
        )
        second_task = functions.create_task(second_p_item)
        self.mock_ctx.datastores.task_store.create_task(second_task)

        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="p_item",
                    field="data__count",
                    operator="lte",
                    value=first_p_item.data.get("count"),
                )
            ],
        )

        # Act
        with self.dbconn.session.begin() as session:
            query = session.query(models.TaskDB)
            query = filters.apply_filter(models.TaskDB, query, f_req)
            results = query.all()

            # Assert
            self.assertEqual(len(results), 2)
            self.assertEqual(results[0].p_item["data"]["id"], first_p_item.data.get("id"))
            self.assertEqual(results[1].p_item["data"]["id"], second_p_item.data.get("id"))

        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="p_item",
                    field="data__count",
                    operator="<=",
                    value=first_p_item.data.get("count"),
                )
            ],
        )

        # Act
        with self.dbconn.session.begin() as session:
            query = session.query(models.TaskDB)
            query = filters.apply_filter(models.TaskDB, query, f_req)
            results = query.all()

            # Assert
            self.assertEqual(len(results), 2)
            self.assertEqual(results[0].p_item["data"]["id"], first_p_item.data.get("id"))
            self.assertEqual(results[1].p_item["data"]["id"], second_p_item.data.get("id"))

    def test_apply_filter_json_like(self):
        # Arrange
        first_p_item = functions.create_p_item(self.organisation.id, 0)
        first_task = functions.create_task(first_p_item)
        self.mock_ctx.datastores.task_store.create_task(first_task)

        second_p_item = functions.create_p_item(self.organisation.id, 0)
        second_task = functions.create_task(second_p_item)
        self.mock_ctx.datastores.task_store.create_task(second_task)

        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="p_item",
                    field="data__name",
                    operator="like",
                    value=f"%{first_p_item.data.get('name')[0:10]}%",
                )
            ],
        )

        # Act
        with self.dbconn.session.begin() as session:
            query = session.query(models.TaskDB)
            query = filters.apply_filter(models.TaskDB, query, f_req)
            results = query.all()

            # Assert
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].p_item["data"]["id"], first_p_item.data.get("id"))

    def test_apply_filter_json_not_like(self):
        # Arrange
        first_p_item = functions.create_p_item(self.organisation.id, 0)
        first_task = functions.create_task(first_p_item)
        self.mock_ctx.datastores.task_store.create_task(first_task)

        second_p_item = functions.create_p_item(self.organisation.id, 0)
        second_task = functions.create_task(second_p_item)
        self.mock_ctx.datastores.task_store.create_task(second_task)

        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="p_item",
                    field="data__name",
                    operator="not_like",
                    value=f"%{first_p_item.data.get('name')[0:10]}%",
                )
            ],
        )

        # Act
        with self.dbconn.session.begin() as session:
            query = session.query(models.TaskDB)
            query = filters.apply_filter(models.TaskDB, query, f_req)
            results = query.all()

            # Assert
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].p_item["data"]["id"], second_p_item.data.get("id"))

    def test_apply_filter_json_ilike(self):
        # Arrange
        first_p_item = functions.create_p_item(self.organisation.id, 0)
        first_task = functions.create_task(first_p_item)
        self.mock_ctx.datastores.task_store.create_task(first_task)

        second_p_item = functions.create_p_item(self.organisation.id, 0)
        second_task = functions.create_task(second_p_item)
        self.mock_ctx.datastores.task_store.create_task(second_task)

        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="p_item",
                    field="data__name",
                    operator="ilike",
                    value=f"%{first_p_item.data.get('name')[0:10].upper()}%",
                )
            ],
        )

        # Act
        with self.dbconn.session.begin() as session:
            query = session.query(models.TaskDB)
            query = filters.apply_filter(models.TaskDB, query, f_req)
            results = query.all()

            # Assert
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].p_item["data"]["id"], first_p_item.data.get("id"))

    def test_apply_filter_json_not_ilike(self):
        # Arrange
        first_p_item = functions.create_p_item(self.organisation.id, 0)
        first_task = functions.create_task(first_p_item)
        self.mock_ctx.datastores.task_store.create_task(first_task)

        second_p_item = functions.create_p_item(self.organisation.id, 0)
        second_task = functions.create_task(second_p_item)
        self.mock_ctx.datastores.task_store.create_task(second_task)

        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="p_item",
                    field="data__name",
                    operator="not_ilike",
                    value=f"%{first_p_item.data.get('name')[0:10].upper()}%",
                )
            ],
        )

        # Act
        with self.dbconn.session.begin() as session:
            query = session.query(models.TaskDB)
            query = filters.apply_filter(models.TaskDB, query, f_req)
            results = query.all()

            # Assert
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].p_item["data"]["id"], second_p_item.data.get("id"))

    def test_apply_filter_json_in(self):
        # Arrange
        first_p_item = functions.create_p_item(self.organisation.id, 0)
        first_task = functions.create_task(first_p_item)
        self.mock_ctx.datastores.task_store.create_task(first_task)

        second_p_item = functions.create_p_item(self.organisation.id, 0)
        second_task = functions.create_task(second_p_item)
        self.mock_ctx.datastores.task_store.create_task(second_task)

        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="p_item",
                    field="data__name",
                    operator="in",
                    value=[first_p_item.data.get("name"), second_p_item.data.get("name")],
                )
            ],
        )

        # Act
        with self.dbconn.session.begin() as session:
            query = session.query(models.TaskDB)
            query = filters.apply_filter(models.TaskDB, query, f_req)
            results = query.all()

            # Assert
            self.assertEqual(len(results), 2)
            self.assertEqual(results[0].p_item["data"]["id"], first_p_item.data.get("id"))
            self.assertEqual(results[1].p_item["data"]["id"], second_p_item.data.get("id"))

    def test_apply_filter_json_not_in(self):
        # Arrange
        first_p_item = functions.create_p_item(self.organisation.id, 0)
        first_task = functions.create_task(first_p_item)
        self.mock_ctx.datastores.task_store.create_task(first_task)

        second_p_item = functions.create_p_item(self.organisation.id, 0)
        second_task = functions.create_task(second_p_item)
        self.mock_ctx.datastores.task_store.create_task(second_task)

        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="p_item",
                    field="data__name",
                    operator="not_in",
                    value=[first_p_item.data.get("name")],
                )
            ],
        )

        # Act
        with self.dbconn.session.begin() as session:
            query = session.query(models.TaskDB)
            query = filters.apply_filter(models.TaskDB, query, f_req)
            results = query.all()

            # Assert
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].p_item["data"]["id"], second_p_item.data.get("id"))

    def test_apply_filter_json_contains(self):
        # Arrange
        first_p_item = functions.create_p_item(self.organisation.id, 0)
        first_task = functions.create_task(first_p_item)
        self.mock_ctx.datastores.task_store.create_task(first_task)

        second_p_item = functions.create_p_item(self.organisation.id, 0)
        second_task = functions.create_task(second_p_item)
        self.mock_ctx.datastores.task_store.create_task(second_task)

        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="p_item",
                    field="data__name",
                    operator="contains",
                    value=first_p_item.data.get("name")[0:10],
                )
            ],
        )

        # Act
        with self.dbconn.session.begin() as session:
            query = session.query(models.TaskDB)
            query = filters.apply_filter(models.TaskDB, query, f_req)
            results = query.all()

            # Assert
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].p_item["data"]["id"], first_p_item.data.get("id"))

    @unittest.skip("TODO")
    def test_apply_filter_json_match(self):
        # Arrange
        first_p_item = functions.create_p_item(self.organisation.id, 0)
        first_task = functions.create_task(first_p_item)
        self.mock_ctx.datastores.task_store.create_task(first_task)

        second_p_item = functions.create_p_item(self.organisation.id, 0)
        second_task = functions.create_task(second_p_item)
        self.mock_ctx.datastores.task_store.create_task(second_task)

        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="p_item",
                    field="data",
                    operator="match",
                    value=first_p_item.data.get("name")[0:10],
                )
            ],
        )

        # Act
        with self.dbconn.session.begin() as session:
            query = session.query(models.TaskDB)
            query = filters.apply_filter(models.TaskDB, query, f_req)
            results = query.all()

            # Assert
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].p_item["data"]["id"], first_p_item.data.get("id"))

    def test_apply_filter_json_starts_with(self):
        # Arrange
        first_p_item = functions.create_p_item(self.organisation.id, 0)
        first_task = functions.create_task(first_p_item)
        self.mock_ctx.datastores.task_store.create_task(first_task)

        second_p_item = functions.create_p_item(self.organisation.id, 0)
        second_task = functions.create_task(second_p_item)
        self.mock_ctx.datastores.task_store.create_task(second_task)

        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="p_item",
                    field="data__name",
                    operator="starts_with",
                    value=first_p_item.data.get("name")[0:10],
                )
            ],
        )

        # Act
        with self.dbconn.session.begin() as session:
            query = session.query(models.TaskDB)
            query = filters.apply_filter(models.TaskDB, query, f_req)
            results = query.all()

            # Assert
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].p_item["data"]["id"], first_p_item.data.get("id"))

    def test_apply_filter_jsonb_contains(self):
        # Arrange
        first_p_item = functions.create_p_item(
            self.organisation.id,
            0,
            functions.TestModel(id=uuid.uuid4().hex, name=uuid.uuid4().hex, count=1, categories=["test-a", "test-b"]),
        )
        first_task = functions.create_task(first_p_item)
        self.mock_ctx.datastores.task_store.create_task(first_task)

        second_p_item = functions.create_p_item(
            self.organisation.id,
            0,
            functions.TestModel(id=uuid.uuid4().hex, name=uuid.uuid4().hex, count=2, categories=["test-a"]),
        )
        second_task = functions.create_task(second_p_item)
        self.mock_ctx.datastores.task_store.create_task(second_task)

        third_p_item = functions.create_p_item(
            self.organisation.id,
            0,
            functions.TestModel(id=uuid.uuid4().hex, name=uuid.uuid4().hex, count=3, categories=["test-b"]),
        )
        third_task = functions.create_task(third_p_item)
        self.mock_ctx.datastores.task_store.create_task(third_task)

        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="p_item",
                    field="data",
                    operator="@>",
                    value=json.dumps({"categories": ["test-a"]}),
                )
            ],
        )

        # Act
        with self.dbconn.session.begin() as session:
            query = session.query(models.TaskDB)
            query = filters.apply_filter(models.TaskDB, query, f_req)
            results = query.all()

            print(compile_query_postgres(query))

            # Assert
            self.assertEqual(len(results), 2)
            self.assertEqual(results[0].p_item["data"]["id"], first_p_item.data.get("id"))
            self.assertEqual(results[1].p_item["data"]["id"], second_p_item.data.get("id"))

    @unittest.skip("TODO")
    def test_apply_filter_jsonb_is_contained_by(self):
        # Arrange
        first_p_item = functions.create_p_item(
            self.organisation.id,
            0,
            functions.TestModel(id=uuid.uuid4().hex, name=uuid.uuid4().hex, count=1, categories=["test-a", "test-b"]),
        )
        first_task = functions.create_task(first_p_item)
        self.mock_ctx.datastores.task_store.create_task(first_task)

        second_p_item = functions.create_p_item(
            self.organisation.id,
            0,
            functions.TestModel(id=uuid.uuid4().hex, name=uuid.uuid4().hex, count=2, categories=["test-a"]),
        )
        second_task = functions.create_task(second_p_item)
        self.mock_ctx.datastores.task_store.create_task(second_task)

        third_p_item = functions.create_p_item(
            self.organisation.id,
            0,
            functions.TestModel(id=uuid.uuid4().hex, name=uuid.uuid4().hex, count=3, categories=["test-b"]),
        )
        third_task = functions.create_task(third_p_item)
        self.mock_ctx.datastores.task_store.create_task(third_task)

        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="p_item",
                    field="data",
                    operator="<@",
                    value=json.dumps({"categories": ["test-a"]}),
                )
            ],
        )

        # Act
        with self.dbconn.session.begin() as session:
            query = session.query(models.TaskDB)
            query = filters.apply_filter(models.TaskDB, query, f_req)
            results = query.all()

            print(compile_query_postgres(query))
            breakpoint()

            # Assert
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].p_item["data"]["id"], first_p_item.data.get("id"))

    @unittest.skip("TODO")
    def test_apply_filter_jsonb_exists(self):
        # Arrange
        first_p_item = functions.create_p_item(
            self.organisation.id,
            0,
            functions.TestModel(id=uuid.uuid4().hex, name=uuid.uuid4().hex, count=1, categories=["test-a", "test-b"]),
        )
        first_task = functions.create_task(first_p_item)
        self.mock_ctx.datastores.task_store.create_task(first_task)

        second_p_item = functions.create_p_item(
            self.organisation.id,
            0,
            functions.TestModel(
                id=uuid.uuid4().hex,
                name=uuid.uuid4().hex,
                count=2,
                child=functions.TestModel(id=uuid.uuid4().hex, name=uuid.uuid4().hex, count=1),
            ),
        )
        second_task = functions.create_task(second_p_item)
        self.mock_ctx.datastores.task_store.create_task(second_task)

        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="p_item",
                    field="data",
                    operator="@?",
                    value="child",
                )
            ],
        )

        # Act
        with self.dbconn.session.begin() as session:
            query = session.query(models.TaskDB)
            query = filters.apply_filter(models.TaskDB, query, f_req)
            results = query.all()

            print(compile_query_postgres(query))
            breakpoint()

            # Assert
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].p_item["data"]["id"], second_p_item.data.get("id"))

    def test_apply_filter_top_level(self):
        # Arrange
        first_p_item = functions.create_p_item(self.organisation.id, 0)
        first_task = functions.create_task(first_p_item)
        self.mock_ctx.datastores.task_store.create_task(first_task)

        second_p_item = functions.create_p_item(self.organisation.id, 0)
        second_task = functions.create_task(second_p_item)
        self.mock_ctx.datastores.task_store.create_task(second_task)

        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="id",
                    field=None,
                    operator="eq",
                    value=first_task.id.hex,
                )
            ],
        )

        # Act
        with self.dbconn.session.begin() as session:
            query = session.query(models.TaskDB)
            query = filters.apply_filter(models.TaskDB, query, f_req)
            results = query.all()

            # Assert
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].id, first_task.id)

    def test_apply_filter_multiple_filters_and(self):
        # Arrange
        first_p_item = functions.create_p_item(self.organisation.id, 0)
        first_task = functions.create_task(first_p_item)
        self.mock_ctx.datastores.task_store.create_task(first_task)

        f_req = filters.FilterRequest(
            filters={
                "and": [
                    filters.Filter(
                        column="id",
                        field=None,
                        operator="eq",
                        value=first_task.id.hex,
                    ),
                    filters.Filter(
                        column="p_item",
                        field="data__id",
                        operator="eq",
                        value=first_p_item.data.get("id"),
                    ),
                ]
            },
        )

        # Act
        with self.dbconn.session.begin() as session:
            query = session.query(models.TaskDB)
            query = filters.apply_filter(models.TaskDB, query, f_req)
            results = query.all()

            # Assert
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].id, first_task.id)
            self.assertEqual(results[0].p_item["data"]["id"], first_p_item.data.get("id"))

    def test_apply_filter_multiple_filters_or(self):
        # Arrange
        first_p_item = functions.create_p_item(self.organisation.id, 0)
        first_task = functions.create_task(first_p_item)
        self.mock_ctx.datastores.task_store.create_task(first_task)

        second_p_item = functions.create_p_item(self.organisation.id, 0)
        second_task = functions.create_task(second_p_item)
        self.mock_ctx.datastores.task_store.create_task(second_task)

        f_req = filters.FilterRequest(
            filters={
                "or": [
                    filters.Filter(
                        column="id",
                        field=None,
                        operator="eq",
                        value=first_task.id.hex,
                    ),
                    filters.Filter(
                        column="id",
                        field=None,
                        operator="eq",
                        value=second_task.id.hex,
                    ),
                ]
            },
        )

        # Act
        with self.dbconn.session.begin() as session:
            query = session.query(models.TaskDB)
            query = filters.apply_filter(models.TaskDB, query, f_req)
            results = query.all()

            # Assert
            self.assertEqual(len(results), 2)
            self.assertEqual(results[0].id, first_task.id)
            self.assertEqual(results[1].id, second_task.id)

    def test_apply_filter_multiple_filters_not(self):
        # Arrange
        first_p_item = functions.create_p_item(
            self.organisation.id,
            0,
            functions.TestModel(id=uuid.uuid4().hex, name=uuid.uuid4().hex, count=1, categories=["test-a", "test-b"]),
        )
        first_task = functions.create_task(first_p_item)
        self.mock_ctx.datastores.task_store.create_task(first_task)

        second_p_item = functions.create_p_item(
            self.organisation.id,
            0,
            functions.TestModel(id=uuid.uuid4().hex, name=uuid.uuid4().hex, count=2, categories=["test-a"]),
        )
        second_task = functions.create_task(second_p_item)
        self.mock_ctx.datastores.task_store.create_task(second_task)

        third_p_item = functions.create_p_item(
            self.organisation.id,
            0,
            functions.TestModel(id=uuid.uuid4().hex, name=uuid.uuid4().hex, count=3, categories=["test-b"]),
        )
        third_task = functions.create_task(third_p_item)
        self.mock_ctx.datastores.task_store.create_task(third_task)

        f_req = filters.FilterRequest(
            filters={
                "and": [
                    filters.Filter(
                        column="id",
                        field=None,
                        operator="eq",
                        value=first_task.id.hex,
                    ),
                    filters.Filter(
                        column="p_item",
                        field="data",
                        operator="@>",
                        value=json.dumps({"categories": ["test-a"]}),
                    ),
                ],
                "not": [
                    filters.Filter(
                        column="p_item",
                        field="data__count",
                        operator=">",
                        value=1,
                    ),
                ],
            },
        )

        # Act
        with self.dbconn.session.begin() as session:
            query = session.query(models.TaskDB)
            query = filters.apply_filter(models.TaskDB, query, f_req)
            results = query.all()

            # Assert
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].id, first_task.id)
            self.assertEqual(results[0].p_item["data"]["id"], first_p_item.data.get("id"))
