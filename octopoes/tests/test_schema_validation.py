from pathlib import Path

import pytest

from octopoes.ddl.ddl import SchemaLoader, SchemaValidationException

TEST_CASES = [
    ("schema_incorrect_natural_key.graphql", "Natural keys must be defined as fields [type=Animal, natural_key=size]"),
    (
        "schema_directive.graphql",
        "A schema may only define a Type, Enum, Union, or Interface, not Directive [directive=test]",
    ),
    (
        "schema_custom_scalar.graphql",
        "A schema may only define a Type, Enum, Union, or Interface, not Scalar [type=CustomScalar]",
    ),
    (
        "schema_custom_input.graphql",
        "A schema may only define a Type, Enum, Union, or Interface, not Input [type=CatSpeech]",
    ),
    ("schema_reserved_type_name.graphql", "Use of reserved type name is not allowed [type=BaseObject]"),
    ("schema_custom_subscription.graphql", "Use of reserved type name is not allowed [type=Subscription]"),
    ("schema_custom_query.graphql", "Use of reserved type name is not allowed [type=Query]"),
    ("schema_custom_mutation.graphql", "Use of reserved type name is not allowed [type=Mutation]"),
    (
        "schema_no_baseobject_inheritance.graphql",
        "An object must inherit both BaseObject and OOI (missing BaseObject) [type=Test]",
    ),
    ("schema_no_ooi_inheritance.graphql", "An object must inherit both BaseObject and OOI (missing OOI) [type=Test]"),
    (
        "schema_no_baseobject_ooi_inheritance.graphql",
        "An object must inherit both BaseObject and OOI (missing both) [type=Test]",
    ),
    ("schema_no_union_with_u.graphql", "Self-defined unions must start with a U [type=Animals]"),
    ("schema_no_pascalcase.graphql", "Object types must follow PascalCase conventions [type=zooKeeper]"),
    (
        "schema_incomplete_interface.graphql",
        "The BaseObject and OOI interfaces must be implemented properly "
        "[type=ZooKeeper primary_key^object_type^human_readable]",
    ),
]


@pytest.mark.parametrize("schema,expected_output", TEST_CASES)
def test_malformed_graphql_schema_validation(schema: str, expected_output: str) -> None:
    """Parametrized helper function for testing schema validation."""
    with pytest.raises(SchemaValidationException) as exc:
        SchemaLoader((Path(__file__).parent / "fixtures" / schema).read_text())
    assert str(exc.value) in expected_output


def test_valid_graphql_schema_validation() -> None:
    """Test that a valid schema does not raise an exception."""
    SchemaLoader((Path(__file__).parent / "fixtures" / "schema_sample.graphql").read_text())
