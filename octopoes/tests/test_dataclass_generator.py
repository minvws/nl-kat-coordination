from pathlib import Path

from octopoes.ddl.dataclasses import DataclassGenerator
from octopoes.ddl.ddl import SchemaLoader


def test_generate_dataclasses_from_simple_schema(schema_loader):
    generator = DataclassGenerator(schema_loader.complete_schema)

    whiskers = generator.dataclasses["Animal"](name="Whiskers", color="red")
    assert whiskers.object_type == "Animal"
    assert whiskers.human_readable == "Hello: Whiskers"
    assert whiskers.primary_key == "722dfb0a405fe4838ab9751a815ebce6"

    leslie = generator.dataclasses["ZooKeeper"](name="Leslie", pet=whiskers)
    assert leslie.object_type == "ZooKeeper"
    assert leslie.human_readable == "Leslie pets Whiskers"
    assert leslie.primary_key == "936bd20b157951d68e3276ab44e89c20"
