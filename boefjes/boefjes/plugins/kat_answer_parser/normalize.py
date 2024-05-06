import json
from collections.abc import Iterable

from boefjes.job_models import NormalizerMeta
from octopoes.models import OOI
from octopoes.models.ooi.config import Config


def run(normalizer_meta: NormalizerMeta, raw: bytes | str) -> Iterable[OOI]:
    data = json.loads(raw)

    bit_id = data["schema"].removeprefix("/bit/")

    yield Config(
        ooi=normalizer_meta.raw_data.boefje_meta.input_ooi,
        bit_id=bit_id,
        config=data["answer"],
    )
