from typing import Iterator, Union

from dns.message import from_text, Message
from dns.rdata import Rdata
from dns.rdtypes.ANY.SOA import SOA
from octopoes.models import OOI
from octopoes.models.ooi.dns.records import (
    DNSSOARecord,
)
from octopoes.models.ooi.dns.zone import Hostname, DNSZone
from octopoes.models.ooi.network import Network

from job import NormalizerMeta


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterator[OOI]:
    internet = Network(name="internet")

    # parse raw data into dns.message.Message
    section = raw.decode()
    lines = section.split("\n")
    message: Message = from_text("\n".join(lines[1:]))

    input_zone_hostname = Hostname(
        network=internet.reference,
        name=normalizer_meta.boefje_meta.arguments["input"]["hostname"]["name"],
    )

    input_zone = DNSZone(hostname=input_zone_hostname.reference)

    for rrset in message.answer:
        for rr in rrset:
            rr: Rdata

            if isinstance(rr, SOA):
                parent_zone_hostname = Hostname(
                    network=internet.reference, name=str(rrset.name)
                )
                parent_zone = DNSZone(hostname=parent_zone_hostname.reference)
                parent_zone_hostname.dns_zone = parent_zone.reference

                input_zone.parent = parent_zone.reference

                soa_hostname = Hostname(network=internet.reference, name=str(rr.mname))

                yield DNSSOARecord(
                    hostname=parent_zone_hostname.reference,
                    value=str(rr),
                    ttl=rrset.ttl,
                    soa_hostname=soa_hostname.reference,
                    serial=rr.serial,
                    retry=rr.retry,
                    refresh=rr.refresh,
                    expire=rr.expire,
                    minimum=rr.minimum,
                )
                yield soa_hostname
                yield input_zone
                yield parent_zone_hostname
                yield parent_zone
