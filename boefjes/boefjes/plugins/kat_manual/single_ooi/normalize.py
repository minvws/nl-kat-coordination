import json
from collections.abc import Iterable

from boefjes.job_models import NormalizerMeta
from octopoes.models import OOI


def run(normalizer_meta: NormalizerMeta, raw: bytes | str) -> Iterable[OOI]:
    for declaration in json.loads(raw.decode()):
        yield {
            "type": "declaration",
            "ooi": declaration["ooi"],
        }
