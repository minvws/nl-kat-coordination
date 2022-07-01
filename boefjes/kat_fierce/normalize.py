import json
from ipaddress import ip_address, IPv4Address
from typing import Iterator, Union

from octopoes.models import OOI
from octopoes.models.ooi.dns.records import DNSARecord, DNSAAAARecord
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.network import Network, IPAddressV4, IPAddressV6

from job import NormalizerMeta


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterator[OOI]:
    results = json.loads(raw)

    internet = Network(name="internet")
    yield internet

    for _, subdomain in results["subdomains"].items():
        host = Hostname(name=subdomain["url"], network=internet.reference)
        yield host

        sub_ip = subdomain["ip"]
        if isinstance(ip_address(sub_ip), IPv4Address):
            ip = IPAddressV4(network=internet.reference, address=sub_ip)
            dns = DNSARecord(
                hostname=host.reference,
                value=sub_ip,
                address=ip.reference,
            )
        else:
            ip = IPAddressV6(network=internet.reference, address=sub_ip)
            dns = DNSAAAARecord(
                hostname=host.reference,
                value=sub_ip,
                address=ip.reference,
            )
        yield ip
        yield dns
