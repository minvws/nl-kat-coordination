import json
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
Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()


class FilteringTestCase(unittest.TestCase):
    def setUp(self):
        session.add_all(
            [
                TestModel(
                    name="Alice",
                    age=25,
                    height=1.8,
                    is_active=True,
                    data={"foo": "bar", "score": 15, "nested": {"bar": "baz"}},
                ),
                TestModel(
                    name="Bob",
                    age=30,
                    height=1.7,
                    is_active=False,
                    data={"foo": "baz", "score": 25, "nested": {"bar": "baz"}},
                ),
                TestModel(
                    name="Charlie",
                    age=28,
                    height=1.6,
                    is_active=True,
                    data={"foo": "bar", "score": 35, "nested": {"bar": "baz"}},
                ),
            ]
        )
        session.commit()

    def tearDown(self):
        session.query(TestModel).delete()
        session.commit()

    def test_apply_filter_basic(self):
        filter_request = FilterRequest(
            filters={
                "and": [
                    Filter(column="name", operator="eq", value="Alice"),
                    Filter(column="age", operator="eq", value=25),
                    Filter(column="height", operator="eq", value=1.8),
                    Filter(column="is_active", operator="eq", value=True),
                ]
            }
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.all()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "Alice")

    def test_apply_filter_nested_fields(self):
        filter_request = FilterRequest(
            filters={
                "and": [
                    Filter(column="name", operator="eq", value="Alice"),
                    Filter(column="data", field="foo", operator="eq", value="bar"),
                ]
            },
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.all()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "Alice")

    def test_apply_filter_casting(self):
        filter_request = FilterRequest(
            filters={
                "and": [
                    Filter(column="name", operator="eq", value="Alice"),
                    Filter(column="age", operator="eq", value="25"),
                    Filter(column="height", operator="eq", value="1.8"),
                    Filter(column="is_active", operator="eq", value="True"),
                ]
            }
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.all()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "Alice")

    def test_apply_filter_empty_filter_request(self):
        filter_request = FilterRequest(filters={})

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.all()
        self.assertEqual(len(results), 3)

    def test_apply_filter_or(self):
        filter_request = FilterRequest(
            filters={
                "or": [
                    Filter(column="name", operator="eq", value="Alice"),
                    Filter(column="name", operator="eq", value="Bob"),
                ]
            }
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.all()
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].name, "Alice")
        self.assertEqual(results[1].name, "Bob")

    def test_apply_filter_and(self):
        filter_request = FilterRequest(
            filters={
                "and": [
                    Filter(column="name", operator="eq", value="Alice"),
                    Filter(column="age", operator="eq", value=25),
                ]
            }
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.all()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "Alice")

    def test_apply_filter_not(self):
        filter_request = FilterRequest(
            filters={
                "not": [Filter(column="name", operator="eq", value="Alice")],
            }
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.all()
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].name, "Bob")
        self.assertEqual(results[1].name, "Charlie")

    def test_apply_filter_numeric(self):
        filter_request = FilterRequest(
            filters={
                "and": [
                    Filter(column="age", operator="gt", value=25),
                    Filter(column="height", operator="lt", value=1.7),
                ]
            }
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.all()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "Charlie")

    def test_apply_filter_string(self):
        filter_request = FilterRequest(
            filters={
                "and": [
                    Filter(column="name", operator="like", value="A%"),
                    Filter(column="name", operator="like", value="%ce"),
                ]
            }
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.all()

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "Alice")

    def test_apply_filter_boolean(self):
        filter_request = FilterRequest(
            filters={
                "and": [
                    Filter(column="is_active", operator="==", value=True),
                    Filter(column="is_active", operator="!=", value=False),
                ]
            }
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.all()

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].name, "Alice")
        self.assertEqual(results[1].name, "Charlie")

    def test_apply_filter_eq(self):
        filter_request = FilterRequest(
            filters={
                "and": [
                    Filter(column="name", operator="eq", value="Alice"),
                ]
            }
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.all()

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "Alice")

        filter_request = FilterRequest(
            filters={
                "and": [
                    Filter(column="name", operator="==", value="Alice"),
                ]
            }
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.all()

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "Alice")

    def test_apply_filter_json_eq(self):
        filter_request = FilterRequest(
            filters={
                "and": [
                    Filter(column="data", field="foo", operator="eq", value="bar"),
                ]
            }
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.all()

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].name, "Alice")
        self.assertEqual(results[1].name, "Charlie")

        filter_request = FilterRequest(
            filters={
                "and": [
                    Filter(column="data", field="foo", operator="==", value="bar"),
                ]
            }
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.all()

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].name, "Alice")
        self.assertEqual(results[1].name, "Charlie")

    def test_apply_filter_ne(self):
        filter_request = FilterRequest(
            filters={
                "and": [
                    Filter(column="name", operator="ne", value="Alice"),
                ]
            }
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.all()

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].name, "Bob")
        self.assertEqual(results[1].name, "Charlie")

        filter_request = FilterRequest(
            filters={
                "and": [
                    Filter(column="name", operator="!=", value="Alice"),
                ]
            }
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.all()
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].name, "Bob")
        self.assertEqual(results[1].name, "Charlie")

    def test_apply_filter_json_ne(self):
        filter_request = FilterRequest(
            filters={
                "and": [
                    Filter(column="data", field="foo", operator="ne", value="bar"),
                ]
            }
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.all()

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "Bob")

        filter_request = FilterRequest(
            filters={
                "and": [
                    Filter(column="data", field="foo", operator="!=", value="bar"),
                ]
            }
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.all()

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "Bob")

    def test_apply_filter_is(self):
        filter_request = FilterRequest(
            filters=[
                Filter(column="is_active", operator="is", value=True),
            ]
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.all()
        self.assertEqual(len(results), 2)
        self.assertIn("Alice", [r.name for r in results])
        self.assertIn("Charlie", [r.name for r in results])

    def test_apply_filter_is_not(self):
        filter_request = FilterRequest(
            filters=[
                Filter(column="is_active", operator="is_not", value=True),
            ]
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.all()
        self.assertEqual(len(results), 1)
        self.assertIn("Bob", [r.name for r in results])

    def test_apply_filter_gt(self):
        filter_request = FilterRequest(
            filters={
                "and": [
                    Filter(column="age", operator="gt", value=25),
                ]
            }
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.order_by(TestModel.age).all()

        self.assertEqual(len(results), 2)
        self.assertIn("Bob", [r.name for r in results])
        self.assertIn("Charlie", [r.name for r in results])

        filter_request = FilterRequest(
            filters={
                "and": [
                    Filter(column="age", operator=">", value=25),
                ]
            }
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.order_by(TestModel.age).all()

        self.assertEqual(len(results), 2)
        self.assertIn("Bob", [r.name for r in results])
        self.assertIn("Charlie", [r.name for r in results])

    def test_apply_filter_json_gt(self):
        filter_request = FilterRequest(
            filters={
                "and": [
                    Filter(column="data", field="score", operator="gt", value=25),
                ]
            }
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.all()

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "Charlie")

        filter_request = FilterRequest(
            filters={
                "and": [
                    Filter(column="data", field="score", operator=">", value=25),
                ]
            }
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.all()

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "Charlie")

    def test_apply_filter_gte(self):
        filter_request = FilterRequest(
            filters={
                "and": [
                    Filter(column="age", operator="gte", value=25),
                ]
            }
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.order_by(TestModel.age).all()

        self.assertEqual(len(results), 3)
        self.assertIn("Alice", [r.name for r in results])
        self.assertIn("Bob", [r.name for r in results])
        self.assertIn("Charlie", [r.name for r in results])

        filter_request = FilterRequest(
            filters={
                "and": [
                    Filter(column="age", operator=">=", value=25),
                ]
            }
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.order_by(TestModel.age).all()

        self.assertEqual(len(results), 3)
        self.assertIn("Alice", [r.name for r in results])
        self.assertIn("Bob", [r.name for r in results])
        self.assertIn("Charlie", [r.name for r in results])

    def test_apply_filter_json_gte(self):
        filter_request = FilterRequest(
            filters={
                "and": [
                    Filter(column="data", field="score", operator="gte", value=25),
                ]
            }
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.all()

        self.assertEqual(len(results), 2)
        self.assertIn("Bob", [r.name for r in results])
        self.assertIn("Charlie", [r.name for r in results])

        filter_request = FilterRequest(
            filters={
                "and": [
                    Filter(column="data", field="score", operator=">=", value=25),
                ]
            }
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.all()

        self.assertEqual(len(results), 2)
        self.assertIn("Bob", [r.name for r in results])
        self.assertIn("Charlie", [r.name for r in results])

    def test_apply_filter_lt(self):
        filter_request = FilterRequest(
            filters={
                "and": [
                    Filter(column="age", operator="lt", value=28),
                ]
            }
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.order_by(TestModel.age).all()

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "Alice")

        filter_request = FilterRequest(
            filters={
                "and": [
                    Filter(column="age", operator="<", value=28),
                ]
            }
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.order_by(TestModel.age).all()

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "Alice")

    def test_apply_filter_json_lt(self):
        filter_request = FilterRequest(
            filters={
                "and": [
                    Filter(column="data", field="score", operator="lt", value=25),
                ]
            }
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.all()

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "Alice")

        filter_request = FilterRequest(
            filters={
                "and": [
                    Filter(column="data", field="score", operator="<", value=25),
                ]
            }
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.all()

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "Alice")

    def test_apply_filter_lte(self):
        filter_request = FilterRequest(
            filters={
                "and": [
                    Filter(column="age", operator="lte", value=28),
                ]
            }
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.order_by(TestModel.age).all()

        self.assertEqual(len(results), 2)
        self.assertIn("Alice", [r.name for r in results])
        self.assertIn("Charlie", [r.name for r in results])

        filter_request = FilterRequest(
            filters={
                "and": [
                    Filter(column="age", operator="<=", value=28),
                ]
            }
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.order_by(TestModel.age).all()

        self.assertEqual(len(results), 2)
        self.assertIn("Alice", [r.name for r in results])
        self.assertIn("Charlie", [r.name for r in results])

    def test_apply_filter_json_lte(self):
        filter_request = FilterRequest(
            filters={
                "and": [
                    Filter(column="data", field="score", operator="lte", value=25),
                ]
            }
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.all()

        self.assertEqual(len(results), 2)
        self.assertIn("Alice", [r.name for r in results])
        self.assertIn("Bob", [r.name for r in results])

        filter_request = FilterRequest(
            filters={
                "and": [
                    Filter(column="data", field="score", operator="<=", value=25),
                ]
            }
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.all()

        self.assertEqual(len(results), 2)
        self.assertIn("Alice", [r.name for r in results])
        self.assertIn("Bob", [r.name for r in results])

    def test_apply_filter_like(self):
        filter_request = FilterRequest(
            filters={
                "and": [
                    Filter(column="name", operator="like", value="B%"),
                ]
            }
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.order_by(TestModel.name).all()

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "Bob")

    def test_apply_filter_json_like(self):
        filter_request = FilterRequest(
            filters={
                "and": [
                    Filter(column="data", field="foo", operator="like", value="%ar"),
                ]
            }
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.all()
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].name, "Alice")
        self.assertEqual(results[1].name, "Charlie")

    def test_apply_filter_not_like(self):
        filter_request = FilterRequest(
            filters={
                "and": [
                    Filter(column="name", operator="not_like", value="B%"),
                ]
            }
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.order_by(TestModel.name).all()

        self.assertEqual(len(results), 2)
        self.assertIn("Alice", [r.name for r in results])
        self.assertIn("Charlie", [r.name for r in results])

    def test_apply_filter_json_not_like(self):
        filter_request = FilterRequest(
            filters={
                "and": [
                    Filter(column="data", field="foo", operator="not_like", value="%ar"),
                ]
            }
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.all()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "Bob")

    def test_apply_filter_ilike(self):
        filter_request = FilterRequest(
            filters={
                "and": [
                    Filter(column="name", operator="ilike", value="B%"),
                ]
            }
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.order_by(TestModel.name).all()

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "Bob")

    def test_apply_filter_json_ilike(self):
        filter_request = FilterRequest(
            filters={
                "and": [
                    Filter(column="data", field="foo", operator="ilike", value="%AR"),
                ]
            }
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.all()
        self.assertEqual(len(results), 2)
        self.assertIn("Alice", [r.name for r in results])
        self.assertIn("Charlie", [r.name for r in results])

    def test_apply_filter_not_ilike(self):
        filter_request = FilterRequest(
            filters={
                "and": [
                    Filter(column="name", operator="not_ilike", value="B%"),
                ]
            }
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.order_by(TestModel.name).all()

        self.assertEqual(len(results), 2)
        self.assertIn("Alice", [r.name for r in results])
        self.assertIn("Charlie", [r.name for r in results])

    def test_apply_filter_json_not_ilike(self):
        filter_request = FilterRequest(
            filters={
                "and": [
                    Filter(column="data", field="foo", operator="not_ilike", value="%AR"),
                ]
            }
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.all()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "Bob")

    def test_apply_filter_in(self):
        filter_request = FilterRequest(
            filters={
                "and": [
                    Filter(column="name", operator="in", value=["Alice", "Bob"]),
                ]
            }
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.order_by(TestModel.name).all()

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].name, "Alice")
        self.assertEqual(results[1].name, "Bob")

    def test_apply_filter_json_in(self):
        filter_request = FilterRequest(
            filters={
                "and": [
                    Filter(column="data", field="foo", operator="in", value=["bar", "baz"]),
                ]
            }
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.order_by(TestModel.name).all()
        self.assertEqual(len(results), 3)

    def test_apply_filter_not_in(self):
        filter_request = FilterRequest(
            filters={
                "and": [
                    Filter(column="name", operator="not_in", value=["Alice", "Bob"]),
                ]
            }
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.order_by(TestModel.name).all()

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "Charlie")

    def test_apply_filter_json_not_in(self):
        filter_request = FilterRequest(
            filters={
                "and": [
                    Filter(column="data", field="foo", operator="not_in", value=["bar"]),
                ]
            }
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.order_by(TestModel.name).all()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "Bob")

    def test_apply_filter_contains(self):
        filter_request = FilterRequest(
            filters={
                "and": [
                    Filter(column="name", operator="contains", value="li"),
                ]
            }
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.order_by(TestModel.name).all()

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].name, "Alice")

    def test_apply_filter_json_contains(self):
        filter_request = FilterRequest(
            filters={
                "and": [
                    Filter(column="data", field="foo", operator="contains", value="ar"),
                ]
            }
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.order_by(TestModel.name).all()
        self.assertEqual(len(results), 2)
        self.assertIn("Alice", [r.name for r in results])
        self.assertIn("Charlie", [r.name for r in results])

    def test_apply_filter_jsonb_contains(self):
        filter_request = FilterRequest(
            filters=[
                Filter(column="data", operator="@>", value=json.dumps({"foo": "bar"})),
            ]
        )

        query = session.query(TestModel)
        filtered_query = apply_filter(TestModel, query, filter_request)

        results = filtered_query.order_by(TestModel.name).all()
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].name, "Alice")
        self.assertEqual(results[1].name, "Charlie")
