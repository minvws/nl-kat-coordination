import pytest
from octopoes.connector.octopoes import OctopoesAPIConnector

from tests.conftest import seed_system


@pytest.mark.slow
def test_migration(octopoes_api_connector: OctopoesAPIConnector, valid_time):
    seed_system(octopoes_api_connector, valid_time)
