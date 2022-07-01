import json
from ipaddress import IPv4Address, IPv6Address
from typing import List
from unittest import TestCase

from octopoes.models import OOI
from octopoes.models.ooi.dns.records import (
    DNSSPFRecord,
    DNSSPFMechanismIP,
    DNSSPFMechanismNetBlock,
    DNSSPFMechanismHostname,
    DNSTXTRecord,
)
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.findings import KATFindingType, Finding
from octopoes.models.ooi.network import (
    Network,
    IPAddressV4,
    IPAddressV6,
    IPV6NetBlock,
    IPV4NetBlock,
)

from boefjes.kat_spf.normalize import run
from config import settings
from job import NormalizerMeta


def get_dummy_data(filename: str) -> bytes:
    path = settings.base_dir / "tests" / "examples" / filename
    return path.read_bytes()


class DnsTest(TestCase):
    maxDiff = None

    def test_spf_no_findings(self):
        meta = NormalizerMeta.parse_raw(get_dummy_data("spf-normalize.json"))

        oois = list(
            run(
                meta,
                json.dumps({}),
            )
        )
        expected = get_expected_without_findings()

        self.assertCountEqual(expected, oois)

    def test_spf_with_txt_input(self):
        meta = NormalizerMeta.parse_raw(get_dummy_data("spf-normalize-txt-input.json"))

        oois = list(
            run(
                meta,
                json.dumps({}),
            )
        )
        internet = Network(name="internet")

        # noinspection PyTypeChecker
        expected = [internet]

        self.assertCountEqual(expected, oois)

    def test_spf_with_findings(self):
        meta = NormalizerMeta.parse_raw(get_dummy_data("spf-normalize-findings.json"))

        oois = list(
            run(
                meta,
                json.dumps({}),
            )
        )
        expected = get_expected_with_findings(meta)

        self.assertCountEqual(expected, oois)


def get_expected_without_findings() -> List[OOI]:
    internet = Network(name="internet")
    hostnames = [
        Hostname(
            network=internet.reference,
            name="example.nl",
            ttl=1800,
        ),
        Hostname(
            network=internet.reference,
            name="incrediblylonghostnamewhichhasbeenaddedtoincrease.nl",
            ttl=1800,
        ),
        Hostname(
            network=internet.reference,
            name="thecharacterlengthofthisspfrecordandtoexceedthelimits.nl",
            ttl=1800,
        ),
    ]
    record = 'v=spf1 a ip4:185.73.32.14/30 ip4:185.73.32.3 ip6:2001:1af8:2100:b080:1::80/64 ip4:185.73.34.3 ip6:2a05:3f44::2:80 include:incre""diblylonghostnamewhichhasbeenaddedtoincrease.nl include:thecharacterlengthofthisspfrecordandtoexceedthelimits.nl ~mx:innerheight.com -all'
    txt_record = DNSTXTRecord(
        hostname=hostnames[0].reference,
        value=record,
        ttl="1800",
    )
    ip_v4_addresses = [
        IPAddressV4(
            network=internet.reference,
            address=IPv4Address("185.73.32.14"),
            ttl=1800,
        ),
        IPAddressV4(
            network=internet.reference, address=IPv4Address("185.73.32.3"), ttl=1800
        ),
        IPAddressV4(
            network=internet.reference, address=IPv4Address("185.73.34.3"), ttl=1800
        ),
    ]
    ip_v6_addresses = [
        IPAddressV6(
            network=internet.reference,
            address=IPv6Address("2001:1af8:2100:b080:1::80"),
            ttl=1800,
        ),
        IPAddressV6(
            network=internet.reference,
            address=IPv6Address("2a05:3f44::2:80"),
            ttl=1800,
        ),
    ]
    netblocks = [
        IPV4NetBlock(
            start_ip=ip_v4_addresses[0].reference,
            mask="30",
            network=internet.reference,
        ),
        IPV6NetBlock(
            start_ip=ip_v6_addresses[0].reference,
            mask="64",
            network=internet.reference,
        ),
    ]
    mx_hostnames = [
        Hostname(network=internet.reference, name="innerheight.com", ttl=1800)
    ]
    spf_value = "v=spf1 a ip4:185.73.32.14/30 ip4:185.73.32.3 ip6:2001:1af8:2100:b080:1::80/64 ip4:185.73.34.3 ip6:2a05:3f44::2:80 include:incrediblylonghostnamewhichhasbeenaddedtoincrease.nl include:thecharacterlengthofthisspfrecordandtoexceedthelimits.nl ~mx:innerheight.com -all"
    spf_record = DNSSPFRecord(
        value=spf_value,
        all="fail",
        ptr=None,
        include=[hostname.reference for hostname in hostnames[1:]],
        redirect=[],
        ttl=1800,
        dns_txt_record=txt_record.reference,
        hostname=hostnames[0].reference,
    )
    spf_mechanism_ips = [
        DNSSPFMechanismIP(
            qualifier="pass",
            ip=record.reference,
            mechanism=record.reference.class_,
            spf_record=spf_record.reference,
        )
        for record in ip_v4_addresses + ip_v6_addresses
    ]
    spf_mechanism_netblocks = [
        DNSSPFMechanismNetBlock(
            qualifier="pass",
            netblock=record.reference,
            mechanism=record.reference.class_,
            spf_record=spf_record.reference,
        )
        for record in netblocks
    ]
    spf_mechanism_mx_hostnames = [
        DNSSPFMechanismHostname(
            qualifier="softfail",
            hostname=record.reference,
            mechanism="mx",
            spf_record=spf_record.reference,
        )
        for record in mx_hostnames
    ]
    # noinspection PyTypeChecker
    expected = (
        ip_v4_addresses
        + [internet, spf_record]
        + hostnames[1:]
        + ip_v6_addresses
        + mx_hostnames
        + netblocks
        + spf_mechanism_mx_hostnames
        + spf_mechanism_netblocks
        + spf_mechanism_ips
    )
    return expected


def get_expected_with_findings(meta: NormalizerMeta) -> List[OOI]:
    internet = Network(name="internet")

    hostnames = [
        Hostname(
            network=internet.reference,
            name="example.nl",
            ttl=1800,
        ),
        Hostname(
            network=internet.reference,
            name="nu.nl",
            ttl=1800,
        ),
        Hostname(
            network=internet.reference,
            name="nu.nl",
            ttl=1800,
        ),
        Hostname(
            network=internet.reference,
            name="ndfsgsdfjhsfdghsdfgsdfhdfhsdhsdfgdfrearbdgfsbgfu.nl",
            ttl=1800,
        ),
        Hostname(
            network=internet.reference,
            name="example.nl.",
            ttl=1800,
        ),
    ]

    redirect = Hostname(
        network=internet.reference,
        name="example.nl",
        ttl=1800,
    )

    txt_record = DNSTXTRecord(
        hostname=hostnames[-1].reference,
        value="v=spf1 ptr ip4:185.73.32.14/2 ip4:185.73.32.3 exists:nu.nl ip6:2001:1af8:2100:b080:1::80::8/64 ip4:185.73.34.3 ip6:2a05:3f44::2:80 -mx:innerheight.com include:example.nl include:nu.nl include:nu.nl include:ndfsgsdfjhsfdghsdfgsdfhdfhsdhsdfgdfrearbdgfsbgfu.nl redirect:example.nl +all",
        ttl="1800",
    )

    mx_hostnames = [
        Hostname(network=internet.reference, name="innerheight.com", ttl=1800)
    ]

    ip_v4_addresses = [
        IPAddressV4(
            network=internet.reference,
            address=IPv4Address("185.73.32.14"),
            ttl=1800,
        ),
        IPAddressV4(
            network=internet.reference, address=IPv4Address("185.73.32.3"), ttl=1800
        ),
        IPAddressV4(
            network=internet.reference, address=IPv4Address("185.73.34.3"), ttl=1800
        ),
    ]
    ip_v6_addresses = [
        IPAddressV6(
            network=internet.reference,
            address=IPv6Address("2a05:3f44::2:80"),
            ttl=1800,
        ),
    ]

    netblocks = [
        IPV4NetBlock(
            start_ip=ip_v4_addresses[0].reference,
            mask="2",
            network=internet.reference,
        )
    ]

    spf_record = DNSSPFRecord(
        value=meta.boefje_meta.arguments["value"],
        all="pass",
        ptr="pass",
        include=[hostname.reference for hostname in hostnames[:4]],
        redirect=[redirect.reference],
        ttl=1800,
        dns_txt_record=txt_record.reference,
    )

    spf_mechanism_ips = [
        DNSSPFMechanismIP(
            qualifier="pass",
            ip=record.reference,
            mechanism=record.reference.class_,
            spf_record=spf_record.reference,
        )
        for record in ip_v4_addresses + ip_v6_addresses
    ]
    spf_mechanism_netblocks = [
        DNSSPFMechanismNetBlock(
            qualifier="pass",
            netblock=record.reference,
            mechanism=record.reference.class_,
            spf_record=spf_record.reference,
        )
        for record in netblocks
    ]
    spf_mechanism_mx_hostnames = [
        DNSSPFMechanismHostname(
            qualifier="fail",
            hostname=record.reference,
            mechanism="mx",
            spf_record=spf_record.reference,
        )
        for record in mx_hostnames
    ]

    findings = [
        ("KAT-613", "SPF record exceeds allowed length of 255 characters."),
        ("KAT-614", "2001:1af8:2100:b080:1::80::8/64 is not a valid ip6 address."),
        ("KAT-615", "Redirect loop: example.nl."),
        ("KAT-616", "'all' should not be enabled."),
        ("KAT-617", "'exists' should not be used."),
        ("KAT-618", "Include loop: example.nl."),
        ("KAT-619", "'ptr' mechanism should not be used."),
    ]

    finding_types = []
    yielded_findings = []
    for finding in findings:
        finding_type = KATFindingType(id=finding[0])
        finding_types.append(finding_type)
        yielded_findings.append(
            Finding(
                finding_type=finding_type.reference,
                ooi=spf_record.reference,
                description=finding[1],
            )
        )

    # noinspection PyTypeChecker
    return (
        ip_v4_addresses
        + [hostnames[0], spf_record, internet]
        + hostnames[:4]
        + yielded_findings
        + finding_types
        + mx_hostnames
        + ip_v6_addresses
        + netblocks
        + spf_mechanism_mx_hostnames
        + spf_mechanism_netblocks
        + spf_mechanism_ips
    )
