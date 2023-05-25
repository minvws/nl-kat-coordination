import json
from typing import Iterable, Union
from boefjes.job_models import NormalizerMeta
from boefjes.job_models import BoefjeMeta
from octopoes.models import OOI, Reference
from octopoes.models.ooi.dns.records import (
    DNSPTRRecord,
)


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterable[OOI]:
    ip_address = Reference.from_str(normalizer_meta.raw_data.boefje_meta.input_ooi)
    results = json.loads(raw)
    hostname = results["Hostname"]
    dnsptr_ooi = DNSPTRRecord(
        value=hostname, address=ip_address
    )
    yield dnsptr_ooi
