from boefjes.plugins.kat_nmap_tcp.normalize import run
from octopoes.models.ooi.network import IPAddressV4, Network
from tests.loading import get_dummy_data


def test_normalizer():
    input_ooi = IPAddressV4(network=Network(name="internet").reference, address="134.209.85.72")
    output = list(run(input_ooi.serialize(), get_dummy_data("raw/nmap_mispoes.xml")))
    assert len(output) == 15
    for i, out in enumerate(output[:-1]):
        if out.object_type == "IPPort" and output[i + 1].object_type == "Service":
            name = output[i + 1].name
            if out.port == 80:
                assert name == "http"
            elif out.port == 443:
                assert name == "https"
            else:
                assert name != "http"
                assert name != "https"
