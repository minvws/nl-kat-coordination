from enum import Enum
from pathlib import Path
from unittest.mock import patch

import pytest

from octopoes.config.settings import Settings
from octopoes.connectors.services import HTTPService
from octopoes.connectors.services.katalogus import Katalogus
from octopoes.context.context import AppContext
from octopoes.ddl.dataclasses import OOI
from octopoes.ddl.ddl import SchemaLoader
from octopoes.models.organisation import Organisation


class Color(Enum):
    RED = "red"
    GREEN = "green"


class Animal(OOI):
    object_type = "Animal"
    name: str
    color: Color


Animal._natural_key_attrs = ["name"]
Animal._human_readable_format = "Hello: {name}"


class ZooKeeper(OOI):
    object_type = "ZooKeeper"
    name: str
    pet: Animal


ZooKeeper._natural_key_attrs = ["name"]
ZooKeeper._human_readable_format = "{name} pets {pet_name}"


@pytest.fixture
def animal():
    return Animal(name="Whiskers", color=Color.RED)


@pytest.fixture
def zookeeper(animal):
    return ZooKeeper(name="Leslie", pet=animal)


@pytest.fixture
def schema_loader() -> SchemaLoader:
    return SchemaLoader((Path(__file__).parent / "fixtures" / "schema_sample.graphql").read_text())


@pytest.fixture
def organisation() -> Organisation:
    return Organisation(id="123", name="Test Org")


@pytest.fixture
def katalogus(mocker, organisation):
    mock = mocker.Mock(spec=Katalogus)
    mock().name = "Katalogus"
    mock().get_organisation.return_value = organisation
    mock().get_organisations.return_value = [organisation]
    mock().is_healthy.return_value = True
    return mock


@pytest.fixture
def app_context(mocker, katalogus):
    mocker.patch("octopoes.context.context.get_katalogus", katalogus)
    return AppContext()
