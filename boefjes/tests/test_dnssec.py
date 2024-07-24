from boefjes.job_handler import serialize_ooi
from boefjes.plugins.kat_dnssec.normalize import run
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.network import Network
from tests.loading import get_dummy_data


def test_dnssec_unsigned():
    input_ooi = Hostname(network=Network(name="internet").reference, name="example.org")
    output = list(run(serialize_ooi(input_ooi), get_dummy_data("inputs/dnssec-unsigned.txt")))

    assert output[1].primary_key == "Finding|Hostname|internet|example.org|KAT-NO-DNSSEC"


def test_dnssec_invalid():
    input_ooi = Hostname(network=Network(name="internet").reference, name="example.org")
    output = list(run(serialize_ooi(input_ooi), get_dummy_data("inputs/dnssec-self-signed.txt")))

    assert output[1].primary_key == "Finding|Hostname|internet|example.org|KAT-INVALID-DNSSEC"


def test_dnssec_valid():
    input_ooi = Hostname(network=Network(name="internet").reference, name="example.org")
    output = list(run(serialize_ooi(input_ooi), get_dummy_data("inputs/dnssec-valid.txt")))

    assert len(output) == 0
