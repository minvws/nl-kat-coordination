from bits.spf_discovery.spf_discovery import run
from octopoes.models import Reference
from octopoes.models.ooi.dns.records import DNSTXTRecord
from octopoes.models.ooi.email_security import DNSSPFRecord, DNSSPFMechanismIP
from octopoes.models.ooi.findings import KATFindingType
from octopoes.models.ooi.network import IPAddressV4


def test_spf_discovery_simple_success():
    dnstxt_record = DNSTXTRecord(
        hostname=Reference.from_str("Hostname|internet|example.com."),
        value="v=spf1 ip4:1.1.1.1 ~all exp=explain._spf.example.com",
    )

    results = list(run(dnstxt_record, []))

    spf_record = DNSSPFRecord(
        dns_txt_record=dnstxt_record.reference,
        value="v=spf1 ip4:1.1.1.1 ~all exp=explain._spf.example.com",
        ttl=None,
        all="~",
        exp="explain._spf.example.com",
    )

    assert results[-1].dict() == spf_record.dict()

    assert results[0].dict() == IPAddressV4(address="1.1.1.1", network=Reference.from_str("Network|internet")).dict()

    assert (
        results[1].dict()
        == DNSSPFMechanismIP(
            ip=Reference.from_str("IPAddressV4|internet|1.1.1.1"), spf_record=spf_record.reference, mechanism="ip4"
        ).dict()
    )


def test_spf_discovery_invalid_():
    dnstxt_record = DNSTXTRecord(
        hostname=Reference.from_str("Hostname|internet|example.com."),
        value="v=spf1 assdfsdf w rgw",
    )

    results = list(run(dnstxt_record, []))

    assert results[0].dict() == KATFindingType(id="KAT-INVALID-SPF")


def test_spf_discovery_intermediate_success():
    dnstxt_record = DNSTXTRecord(
        hostname=Reference.from_str("Hostname|internet|example1.com."),
        value="v=spf1 a:example.com mx mx:deferrals.domain.com ptr:otherdomain.com "
        "exists:example4.com ?include:example2.com ~all",
    )
    results = list(run(dnstxt_record, []))

    assert len(results) == 12
