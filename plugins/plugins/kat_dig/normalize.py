from collections.abc import Iterable

from katalogus.boefjes.models import NormalizerOutput
from octopoes.models.ooi.dns.records import DNSRecord


def run(input_ooi: dict, raw: bytes) -> Iterable[NormalizerOutput]:
    lines = [line.split("\t") for line in raw.decode().split("\n") if not line.startswith(";") and line]
    hostnames = set()

    for line in lines:
        hostname, ttl, record_class, record_type, content = line
        hostnames.add(hostname.rstrip("."))

        # TODO
        yield DNSRecord(
            object_type="DNSRecord",
            hostname=hostname,
            ttl=int(ttl),
            dns_record_type=record_type,
            value=content,
        )

    for hostname in hostnames:
        yield hostname
