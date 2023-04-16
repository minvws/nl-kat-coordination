import json
from typing import Iterator, Union

from boefjes.job_models import NormalizerMeta
from octopoes.models import OOI


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterator[OOI]:
    for declaration in json.loads(raw.decode()):
        yield {
            "type": "declaration",
            "ooi": declaration["ooi"],
        }
