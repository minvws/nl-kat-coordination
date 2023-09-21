import os
import unittest

from scheduler.storage.filters import Filter, FilterRequest, apply_filter
from sqlalchemy import Boolean, Column, Float, Integer, String, create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


class TestModel(Base):
    __tablename__ = "test"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    age = Column(Integer)
    height = Column(Float)
    is_active = Column(Boolean)
    data = Column(JSONB, nullable=False)


# Database setup
engine = create_engine(f"{os.getenv('SCHEDULER_DB_URI')}")
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()


class FilteringTestCase(unittest.TestCase):
    def setUp(self):
        session.add_all([
            TestModel(name="Alice", age=20, height=1.8, is_active=True, data={"foo": "bar"}),
            TestModel(name="Bob", age=30, height=1.7, is_active=False, data={"foo": "baz"}),
            TestModel(name="Charlie", age=40, height=1.6, is_active=True, data={"foo": "bar"}),
        ])
        session.commit()

    def tearDown(self):
        session.query(TestModel).delete()
        session.commit()

    def test_apply_filter_basic(self):
        filter_request = FilterRequest(
            filters={"and": [
                Filter(column="name", operator="eq", value="Alice"),
                Filter(column="age", operator="eq", value=20),
                Filter(column="height", operator="eq", value=1.8),
                Filter(column="is_active", operator="eq", value=True),
            ]}
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.all()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "Alice")

    def test_apply_filter_nested_fields(self):
        filter_request = FilterRequest(
            filters={"and": [
                Filter(column="name", operator="eq", value="Alice"),
                Filter(column="data", field="foo", operator="eq", value="bar"),
            ]},
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.all()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "Alice")
