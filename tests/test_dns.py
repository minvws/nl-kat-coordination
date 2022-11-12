from ipaddress import IPv4Address, IPv6Address
from unittest import TestCase

from boefjes.job_handler import serialize_ooi

from octopoes.models import Reference
from octopoes.models.ooi.dns.records import (
    DNSARecord,
    DNSAAAARecord,
    DNSTXTRecord,
    DNSMXRecord,
    DNSNSRecord,
    DNSSOARecord,
    DNSCNAMERecord,
)
from octopoes.models.ooi.dns.zone import Hostname, DNSZone
from octopoes.models.ooi.network import Network, IPAddressV4, IPAddressV6

from boefjes.plugins.kat_dns.normalize import run
from boefjes.plugins.kat_dns_zone.normalize import run as run_zone_normalizer
from boefjes.job_models import NormalizerMeta, BoefjeMeta, Normalizer, Boefje
from tests.stubs import get_dummy_data


class DnsTest(TestCase):
    maxDiff = None

    def test_dns_normalizer(self):
        meta = NormalizerMeta.parse_raw(get_dummy_data("dns-normalize.json"))

        oois = list(
            run(
                meta,
                get_dummy_data("inputs/dns-result-example.nl.txt"),
            )
        )
        internet = Network(name="internet")

        zone_hostname = Hostname(name="example.nl.", network=internet.reference)
        zone = DNSZone(hostname=zone_hostname.reference)
        zone_hostname.dns_zone = zone.reference

        input_hostname = Hostname(
            name="example.nl", network=internet.reference, dns_zone=zone.reference
        )

        ip_v4_addresses = [
            IPAddressV4(
                network=internet.reference, address=IPv4Address("94.198.159.35")
            ),
            IPAddressV4(
                network=internet.reference, address=IPv4Address("94.198.159.36")
            ),
        ]
        dns_a_records = [
            DNSARecord(
                hostname=zone_hostname.reference,
                value=str(ip.address),
                address=ip.reference,
                ttl=14364,
            )
            for ip in ip_v4_addresses
        ]
        ip_v6_addresses = [
            IPAddressV6(
                network=internet.reference,
                address=IPv6Address("2a00:d78:0:712:94:198:159:35"),
            ),
            IPAddressV6(
                network=internet.reference,
                address=IPv6Address("2a00:d78:0:712:94:198:159:36"),
            ),
        ]
        dns_aaaa_records = [
            DNSAAAARecord(
                hostname=zone_hostname.reference,
                value=str(ip.address),
                address=ip.reference,
                ttl=14400,
            )
            for ip in ip_v6_addresses
        ]
        dns_txt_records = [
            DNSTXTRecord(
                hostname=zone_hostname.reference,
                value="v=spf1 redirect=spf-a.example.nl",
                ttl=14400,
            )
        ]

        mx_hostnames = [
            Hostname(
                network=internet.reference,
                name="mail.example.nl.",
            ),
            Hostname(
                network=internet.reference,
                name="mail2.example.nl.",
            ),
        ]
        dns_mx_records = [
            DNSMXRecord(
                hostname=zone_hostname.reference,
                value=f"10 {mx_rec.name}",
                ttl=14400,
                mail_hostname=mx_rec.reference,
                preference=10,
            )
            for mx_rec in mx_hostnames
        ]

        ns_hostnames = [
            Hostname(name=value, network=internet.reference)
            for value in [
                "ns3.examplenl.org.",
                "ns1.examplenl.nl.",
                "ns2.examplenl.eu.",
                "ns0.examplenl.com.",
            ]
        ]

        ns_records = [
            DNSNSRecord(
                hostname=zone_hostname.reference,
                value=ns_hostname.name,
                name_server_hostname=ns_hostname.reference,
                ttl=2634,
            )
            for ns_hostname in ns_hostnames
        ]

        soa_hostname = Hostname(
            network=internet.reference,
            name="ns1.examplenl.nl.",
            dns_zone=zone.reference,
        )
        soa_record = DNSSOARecord(
            hostname=zone_hostname.reference,
            value="ns1.examplenl.nl. hostmaster.sidn.nl. 2021111101 14400 7200 1209600 86400",
            soa_hostname=soa_hostname.reference,
            ttl=14340,
            serial=2021111101,
            retry=7200,
            refresh=14400,
            expire=1209600,
            minimum=86400,
        )

        # noinspection PyTypeChecker
        expected = (
            [zone_hostname, zone, input_hostname]
            + ip_v4_addresses
            + dns_a_records
            + ip_v6_addresses
            + dns_aaaa_records
            + dns_txt_records
            + mx_hostnames
            + dns_mx_records
            + ns_hostnames
            + ns_records
            + [soa_record]
        )

        self.assertCountEqual(expected, oois)

    def test_dns_normalizer_cname(self):

        meta = NormalizerMeta(
            id="",
            normalizer=Normalizer(id="kat_dns_normalize"),
            boefje_meta=BoefjeMeta(
                id="1234",
                boefje=Boefje(id="dns-records"),
                organization="_dev",
                input_ooi="Hostname|internet|www.example.nl.",
                arguments={
                    "domain": "www.example.nl.",
                    "input": {"name": "www.example.nl."},
                },
            ),
        )

        oois = list(
            run(
                meta,
                get_dummy_data("inputs/dns-result-www.example.nl.txt"),
            )
        )

        internet = Network(name="internet")

        zone_hostname = Hostname(
            network=internet.reference,
            name="example.nl.",
        )
        zone = DNSZone(
            hostname=zone_hostname.reference,
        )
        zone_hostname.dns_zone = zone.reference

        input_hostname = Hostname(
            network=internet.reference,
            name="www.example.nl.",
            dns_zone=zone.reference,
        )
        cname_target = Hostname(
            network=internet.reference,
            name="webredir.examplenl.nl.",
        )

        soa_hostname = Hostname(network=internet.reference, name="ns1.examplenl.nl.")
        soa_record = DNSSOARecord(
            hostname=zone_hostname.reference,
            value="ns1.examplenl.nl. hostmaster.sidn.nl. 2021111101 14400 7200 1209600 86400",
            ttl=14340,
            soa_hostname=soa_hostname.reference,
            serial=2021111101,
            refresh=14400,
            retry=7200,
            expire=1209600,
            minimum=86400,
        )

        cname_record = DNSCNAMERecord(
            hostname=input_hostname.reference,
            value=cname_target.name,
            ttl=10800,
            target_hostname=cname_target.reference,
        )

        ip_address = IPAddressV4(
            network=internet.reference, address=IPv4Address("94.198.159.35")
        )
        dns_a_record = DNSARecord(
            hostname=cname_target.reference,
            address=ip_address.reference,
            value=str(ip_address.address),
            ttl=10800,
        )

        expected = [
            zone,
            zone_hostname,
            soa_hostname,
            soa_record,
            cname_target,
            cname_record,
            ip_address,
            dns_a_record,
            input_hostname,
        ]
        self.assertCountEqual(expected, oois)

    def test_parse_record_null_mx_record(self):

        meta = NormalizerMeta(
            id="",
            normalizer=Normalizer(id="kat_dns_normalize"),
            boefje_meta=BoefjeMeta(
                id="1234",
                boefje=Boefje(id="dns-records"),
                organization="_dev",
                input_ooi="Hostname|internet|english.example.nl.",
                arguments={
                    "domain": "english.example.nl",
                    "input": {"name": "english.example.nl"},
                },
            ),
        )

        answer = """\
RESOLVER: 2001:b88:1002::10
id 21479
opcode QUERY
rcode NOERROR
flags QR RD RA
;QUESTION
english.example.nl. IN MX
;ANSWER
english.example.nl. 60 IN CNAME redir.example.nl.
redir.example.nl. 14400 IN MX 0 .
;AUTHORITY
;ADDITIONAL
"""
        oois = list(run(meta, answer.encode()))

        internet = Network(name="internet")
        input_hostname = Hostname(
            network=internet.reference,
            name="english.example.nl",
        )
        input_fqdn = Hostname(
            network=internet.reference,
            name="english.example.nl.",
        )

        cname_target = Hostname(network=internet.reference, name="redir.example.nl.")
        cname_record = DNSCNAMERecord(
            hostname=input_fqdn.reference,
            value="redir.example.nl.",
            ttl=60,
            target_hostname=cname_target.reference,
        )
        mx_record = DNSMXRecord(
            hostname=cname_target.reference,
            value="0 .",
            ttl=14400,
            preference=0,
        )
        self.assertCountEqual(
            [cname_target, cname_record, mx_record, input_fqdn, input_hostname],
            oois,
        )

    def test_parse_cname_soa(self):

        meta = NormalizerMeta(
            id="",
            normalizer=Normalizer(id="kat_dns_normalize"),
            boefje_meta=BoefjeMeta(
                id="1234",
                boefje=Boefje(id="dns-records"),
                organization="_dev",
                input_ooi="Hostname|internet|www.example.com",
                arguments={
                    "domain": "www.example.com",
                    "input": {"name": "www.example.com"},
                },
            ),
        )

        oois = list(
            run(
                meta,
                get_dummy_data("inputs/dns-result-example.com-cnames.txt"),
            )
        )

        internet = Network(name="internet")

        zone_hostname = Hostname(
            network=internet.reference,
            name="example.com.",
        )
        zone = DNSZone(
            hostname=zone_hostname.reference,
        )
        zone_hostname.dns_zone = zone.reference

        input_hostname = Hostname(
            network=internet.reference,
            name="www.example.com",
            dns_zone=zone.reference,
        )

        input_fqdn = Hostname(
            network=internet.reference,
            name="www.example.com.",
        )
        cname_record = DNSCNAMERecord(
            hostname=input_fqdn.reference,
            value="example.com.",
            ttl=60,
            target_hostname=zone_hostname.reference,
        )
        ip_address = IPAddressV4(
            network=internet.reference, address=IPv4Address("94.198.159.35")
        )
        a_record = DNSARecord(
            hostname=zone_hostname.reference,
            address=ip_address.reference,
            value=str(ip_address.address),
            ttl=60,
        )
        soa_hostname = Hostname(network=internet.reference, name="ns.icann.org.")
        ns_hostnames = [
            Hostname(name=value, network=internet.reference)
            for value in [
                "a.iana-servers.net.",
                "b.iana-servers.net.",
            ]
        ]
        ns_records = [
            DNSNSRecord(
                hostname=zone_hostname.reference,
                value=ns_hostname.name,
                name_server_hostname=ns_hostname.reference,
                ttl=60,
            )
            for ns_hostname in ns_hostnames
        ]
        soa_record = DNSSOARecord(
            hostname=zone_hostname.reference,
            value="ns.icann.org. noc.dns.icann.org. 2022040432 7200 3600 1209600 3600",
            ttl=21,
            soa_hostname=soa_hostname.reference,
            serial=2022040432,
            retry=3600,
            refresh=7200,
            expire=1209600,
            minimum=3600,
        )
        txt_record = DNSTXTRecord(
            hostname=zone_hostname.reference,
            value="v=spf1 -all",
            ttl=60,
        )
        mx_record = DNSMXRecord(
            hostname=zone_hostname.reference,
            value="0 example.com.",
            ttl=60,
            mail_hostname=zone_hostname.reference,
            preference=0,
        )
        self.assertCountEqual(
            [
                zone,
                zone_hostname,
                input_fqdn,
                cname_record,
                ip_address,
                a_record,
                soa_record,
                txt_record,
                mx_record,
                input_hostname,
                soa_hostname,
            ]
            + ns_hostnames
            + ns_records,
            oois,
        )

    def test_find_parent_dns_zone(self):

        input_ = serialize_ooi(
            DNSZone(
                hostname=Hostname(
                    network=Reference.from_str("Network|internet"),
                    name="sub.example.nl.",
                ).reference
            )
        )

        meta = NormalizerMeta(
            id="",
            normalizer=Normalizer(id="kat_dns_normalize"),
            boefje_meta=BoefjeMeta(
                id="1234",
                boefje=Boefje(id="dns-records"),
                organization="_dev",
                input_ooi="DnsZone|internet|sub.example.nl.",
                arguments={"input": input_},
            ),
        )

        oois = list(
            run_zone_normalizer(
                meta,
                get_dummy_data("inputs/dns-zone-result-sub.example.nl.txt"),
            )
        )

        internet = Network(name="internet")

        requested_zone = DNSZone(
            hostname=Hostname(
                network=internet.reference,
                name="sub.example.nl.",
            ).reference
        )
        parent_zone_hostname = Hostname(
            network=internet.reference,
            name="example.nl.",
        )
        parent_zone = DNSZone(hostname=parent_zone_hostname.reference)
        parent_zone_hostname.dns_zone = parent_zone.reference

        requested_zone.parent = parent_zone.reference

        name_server_hostname = Hostname(
            network=internet.reference,
            name="ns1.examplenl.nl.",
        )

        soa_record = DNSSOARecord(
            hostname=parent_zone_hostname.reference,
            value="ns1.examplenl.nl. hostmaster.sidn.nl. 2021111101 14400 7200 1209600 86400",
            ttl=14340,
            soa_hostname=name_server_hostname.reference,
            serial=2021111101,
            retry=7200,
            refresh=14400,
            expire=1209600,
            minimum=86400,
        )

        self.assertCountEqual(
            [
                requested_zone,
                parent_zone,
                parent_zone_hostname,
                name_server_hostname,
                soa_record,
            ],
            oois,
        )
