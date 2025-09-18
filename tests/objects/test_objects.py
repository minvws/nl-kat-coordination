from objects.models import Hostname, Network


def test_query_hostname(xtdb):
    network = Network.objects.create(name="internet")
    Hostname.objects.create(network=network, name="test.com")

    networks = Network.objects.filter(hostname__name="test.com")
    assert networks.count() == 1
