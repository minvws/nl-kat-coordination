from boefjes.job_models import Boefje, BoefjeMeta, Normalizer, NormalizerMeta, RawDataMeta
from boefjes.plugins.kat_rdns.normalize import run
from octopoes.models import Reference
from octopoes.models.ooi.dns.records import DNSPTRRecord
from octopoes.models.ooi.dns.zone import Hostname
from tests.stubs import get_dummy_data

rdns_meta = NormalizerMeta(
    id="",
    normalizer=Normalizer(id="kat_dns_zone_normalize"),
    raw_data=RawDataMeta(
        id="",
        boefje_meta=BoefjeMeta(
            id="1234",
            boefje=Boefje(id="rdns"),
            organization="_dev",
            input_ooi="IPAddressV4|internet|192.0.2.1",
            arguments={"input": {"network": {"name": "internet"}}},
        ),
        mime_types=[{"value": "boefje/rdns"}],
    ),
)


def test_rdns_nxdomain():
    oois = set(run(rdns_meta, get_dummy_data("rdns-nxdomain.txt")))

    assert not oois


returned_oois = {
    DNSPTRRecord(
        object_type="DNSPTRRecord",
        scan_profile=None,
        primary_key="DNSPTRRecord|internet|example.com|internet|192.0.2.1",
        hostname=Reference("Hostname|internet|example.com"),
        dns_record_type="PTR",
        value="1.2.0.192.in-addr.arpa. 86400 IN PTR example.com.",
        ttl=86400,
        address=Reference("IPAddressV4|internet|192.0.2.1"),
    ),
    Hostname(
        object_type="Hostname",
        scan_profile=None,
        primary_key="Hostname|internet|example.com",
        network=Reference("Network|internet"),
        name="example.com",
        dns_zone=None,
        registered_domain=None,
    ),
}


def test_rdns_answer_1():
    oois = set(run(rdns_meta, get_dummy_data("rdns-example1.txt")))

    assert oois == returned_oois


def test_rdns_answer_2():
    oois = set(run(rdns_meta, get_dummy_data("rdns-example2.txt")))

    assert oois == returned_oois
