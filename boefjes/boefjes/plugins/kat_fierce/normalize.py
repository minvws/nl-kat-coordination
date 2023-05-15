import json
from ipaddress import IPv4Address, ip_address
from typing import Iterable, Union

from boefjes.job_models import NormalizerMeta
from octopoes.models import OOI
from octopoes.models.ooi.dns.records import DNSAAAARecord, DNSARecord
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.network import IPAddressV4, IPAddressV6, Network


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterable[OOI]:
    results = json.loads(raw)

    internet = Network(name="internet")
    yield internet

    for _, subdomain in results["subdomains"].items():
        host = Hostname(name=subdomain["url"].rstrip("."), network=internet.reference)
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
