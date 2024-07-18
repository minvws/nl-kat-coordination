import pytest
from octopoes.connector.octopoes import OctopoesAPIConnector

from tests.conftest import seed_system


@pytest.mark.slow
def test_migration(octopoes_api_connector: OctopoesAPIConnector, valid_time):
    seed_system(octopoes_api_connector, valid_time)

    hostname_range = range(0, 20)

    for x in hostname_range:
        seed_system(
            octopoes_api_connector,
            valid_time,
            test_hostname=f"{x}.com",
            test_ip=f"192.0.{x % 7}.{x % 13}",
            test_ipv6=f"{x % 7}e4d:64a2:cb49:bd48:a1ba:def3:d15d:{x % 5}230",
        )

