from unittest import TestCase

from scheduler.models import Base
from scheduler.repositories import sqlalchemy, stores
from sqlalchemy.orm import sessionmaker
from tests.integration.test_api import create_p_item


class TestRepositories(TestCase):
    def setUp(self) -> None:
        self.datastore = sqlalchemy.SQLAlchemy("sqlite:///")
        Base.metadata.create_all(self.datastore.engine)

        self.pq_store = sqlalchemy.PriorityQueueStore(datastore=self.datastore)

    def tearDown(self) -> None:
        session = sessionmaker(bind=self.datastore.engine)()

        for table in Base.metadata.tables.keys():
            session.execute(f"DELETE FROM {table}")

        session.commit()
        session.close()

    def test_push_pop(self) -> None:
        scheduler_id = "scheduler_1"

        item = create_p_item("test", 3, data={"organization": "test"})
        item.scheduler_id = scheduler_id

        self.pq_store.push(scheduler_id, item)
        p_item = self.pq_store.pop(scheduler_id)

        self.assertIsNotNone(p_item)
        self.assertIsNone(p_item.hash)
        self.assertEqual(scheduler_id, p_item.scheduler_id)
        self.assertEqual(3, p_item.priority)
        self.assertEqual({"organization": "test"}, p_item.data)
