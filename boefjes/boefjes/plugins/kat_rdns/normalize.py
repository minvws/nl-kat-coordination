from collections.abc import Iterable

from dns.message import from_text
from dns.rdtypes.ANY.PTR import PTR

from boefjes.job_models import NormalizerMeta
from octopoes.models import OOI, Reference
from octopoes.models.ooi.dns.records import DNSPTRRecord
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.network import Network


def run(normalizer_meta: NormalizerMeta, raw: bytes | str) -> Iterable[OOI]:
    ooi = Reference.from_str(normalizer_meta.raw_data.boefje_meta.input_ooi)
    input_ = normalizer_meta.raw_data.boefje_meta.arguments["input"]
    answers = raw.decode()
    if answers == "NXDOMAIN" or answers == "NoAnswer":
        return
    lines = [line for line in answers.split("\n") if not line.startswith("option")]
    for rrset in from_text("\n".join(lines[1:])).answer:
        for rr in rrset:
            if isinstance(rr, PTR):
                value = rrset.to_text()
                hostname = Hostname(
                    name=rr.to_text().rstrip("."), network=Network(name=input_["network"]["name"]).reference
                )
                yield hostname
                ptr_record = DNSPTRRecord(address=ooi, hostname=hostname.reference, value=value, ttl=rrset.ttl)
                yield ptr_record
