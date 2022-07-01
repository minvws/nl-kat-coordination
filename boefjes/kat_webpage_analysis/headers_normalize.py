import json
from typing import Union, Iterator
from octopoes.models import OOI, Reference
from octopoes.models.ooi.web import HTTPHeader

from job import NormalizerMeta


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterator[OOI]:

    results = json.loads(raw)
    ooi = Reference.from_str(normalizer_meta.boefje_meta.input_ooi)

    for header in results["headers"].items():
        h = HTTPHeader(resource=ooi, key=header[0], value=header[1])
        yield h
