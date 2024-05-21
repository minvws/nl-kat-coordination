import json
from collections.abc import Iterable

from boefjes.job_models import NormalizerOutput
from octopoes.models.ooi.config import Config


def run(input_ooi: dict, raw: bytes) -> Iterable[NormalizerOutput]:
    data = json.loads(raw)

    bit_id = data["schema"].removeprefix("/bit/")

    yield Config(
        ooi=input_ooi["primary_key"],
        bit_id=bit_id,
        config=data["answer"],
    )
