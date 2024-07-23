import pytest
from octopoes.connector.octopoes import OctopoesAPIConnector

from tests.loading import get_dummy_data


@pytest.mark.slow
def test_migration(octopoes_api_connector: OctopoesAPIConnector, valid_time):
    octopoes_api_connector.import_add(get_dummy_data("old_octopoes_dump.json"))

