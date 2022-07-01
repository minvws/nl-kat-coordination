from ipaddress import IPv4Address, IPv6Address
from typing import Iterator, Union, List, Dict

from dns.message import from_text, Message
from dns.name import from_text as name_from_text
from dns.rdata import Rdata
from dns.rdtypes.ANY.CNAME import CNAME
from dns.rdtypes.ANY.MX import MX
from dns.rdtypes.ANY.NS import NS
from dns.rdtypes.ANY.SOA import SOA
from dns.rdtypes.ANY.TXT import TXT
from dns.rdtypes.IN.A import A
from dns.rdtypes.IN.AAAA import AAAA
from octopoes.models import OOI, Reference
from octopoes.models.ooi.dns.records import (
    DNSARecord,
    DNSAAAARecord,
    DNSTXTRecord,
    DNSMXRecord,
    DNSNSRecord,
    DNSSOARecord,
    DNSCNAMERecord,
    DNSRecord,
    NXDOMAIN,
)
from octopoes.models.ooi.dns.zone import Hostname, DNSZone
from octopoes.models.ooi.network import IPAddressV4, IPAddressV6, Network

from job import NormalizerMeta


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterator[OOI]:
    internet = Network(name="internet")

    if raw.decode() == "NXDOMAIN":
        yield NXDOMAIN(
            hostname=Reference.from_str(normalizer_meta.boefje_meta.input_ooi)
        )
        return

    # parse raw data into dns.response.Message
    sections = raw.decode().split("\n\n")
    responses: List[Message] = []
    for section in sections:
        lines = section.split("\n")
        responses.append(from_text("\n".join(lines[1:])))

    zone = None
    hostname_store: Dict[str, Hostname] = {}
    record_store: Dict[str, DNSRecord] = {}

    def register_hostname(name: str) -> Hostname:
        hostname = Hostname(
            network=internet.reference,
            name=name,
        )
        hostname_store[hostname.name] = hostname
        return hostname

    def register_record(record: DNSRecord) -> DNSRecord:
        record_store[record.reference] = record
        return record

    # register argument hostname
    input_hostname = register_hostname(
        normalizer_meta.boefje_meta.arguments["input"]["name"]
    )

    # keep track of discovered zones
    zone_links: Dict[str, DNSZone] = {}

    for response in responses:

        for rrset in response.answer:
            for rr in rrset:
                rr: Rdata

                record_hostname = register_hostname(str(rrset.name))
                default_args = {
                    "hostname": record_hostname.reference,
                    "value": str(rr),
                    "ttl": rrset.ttl,
                }

                # the soa is the zone of itself, and the argument hostname
                if isinstance(rr, SOA):
                    zone = DNSZone(
                        hostname=record_hostname.reference,
                    )
                    zone_links[record_hostname.name] = zone
                    zone_links[input_hostname.name] = zone

                    soa = DNSSOARecord(
                        serial=rr.serial,
                        refresh=rr.refresh,
                        retry=rr.retry,
                        expire=rr.expire,
                        minimum=rr.minimum,
                        soa_hostname=register_hostname(str(rr.mname)).reference,
                        **default_args,
                    )
                    yield soa

                if isinstance(rr, A):
                    ipv4 = IPAddressV4(
                        network=internet.reference, address=IPv4Address(str(rr))
                    )
                    yield ipv4
                    register_record(DNSARecord(address=ipv4.reference, **default_args))

                if isinstance(rr, AAAA):
                    ipv6 = IPAddressV6(
                        network=internet.reference, address=IPv6Address(str(rr))
                    )
                    yield ipv6
                    register_record(
                        DNSAAAARecord(
                            address=ipv6.reference,
                            **default_args,
                        )
                    )

                if isinstance(rr, TXT):
                    default_args["value"] = str(rr).strip('"')
                    register_record(DNSTXTRecord(**default_args))

                if isinstance(rr, MX):
                    mail_hostname_reference = None
                    if str(rr.exchange) != ".":
                        mail_fqdn = register_hostname(str(rr.exchange))
                        mail_hostname_reference = mail_fqdn.reference

                    register_record(
                        DNSMXRecord(
                            mail_hostname=mail_hostname_reference,
                            preference=rr.preference,
                            **default_args,
                        )
                    )

                if isinstance(rr, NS):
                    ns_fqdn = register_hostname(str(rr.target))
                    register_record(
                        DNSNSRecord(
                            name_server_hostname=ns_fqdn.reference,
                            **default_args,
                        )
                    )

                if isinstance(rr, CNAME):
                    target_fqdn = register_hostname(str(rr.target))
                    register_record(
                        DNSCNAMERecord(
                            target_hostname=target_fqdn.reference,
                            **default_args,
                        )
                    )

    # link the hostnames to their discovered zones
    for hostname_, zone in zone_links.items():
        hostname_store[hostname_].dns_zone = zone.reference

    if zone:
        yield zone
    yield from hostname_store.values()
    yield from record_store.values()
