import pytest

from oois.models import Hostname, Network


@pytest.mark.django_db(databases=["xtdb", "default"])
def test_query_hostname(django_xtdb_setup):
    network = Network.objects.create(name="internet")
    Hostname.objects.create(network=network, name="test.com")

    networks = Network.objects.filter(hostname__name="test.com")
    assert networks.count() == 1
