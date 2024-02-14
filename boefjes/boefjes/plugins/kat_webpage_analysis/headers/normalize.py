import json
from collections.abc import Iterable

from boefjes.job_models import NormalizerMeta
from octopoes.models import OOI, Reference
from octopoes.models.ooi.web import HTTPHeader


def run(normalizer_meta: NormalizerMeta, raw: bytes | str) -> Iterable[OOI]:
    # fetch a reference to the original resource where these headers where downloaded from
    resource = Reference.from_str(normalizer_meta.raw_data.boefje_meta.input_ooi)

    for key, value in json.loads(raw).items():
        yield HTTPHeader(
            resource=resource,
            key=key,
            value=value,
        )
