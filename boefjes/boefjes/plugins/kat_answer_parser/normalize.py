import json
from typing import Iterable, Union

from boefjes.job_models import NormalizerMeta
from octopoes.models import OOI
from octopoes.models.ooi.config import Config


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterable[OOI]:
    mime_types = [mime_type["value"] for mime_type in normalizer_meta.raw_data.mime_types]

    if "/bit/port-classification-ip" in mime_types:
        if isinstance(raw, bytes):
            raw = raw.decode()

        yield Config(
            ooi=normalizer_meta.raw_data.boefje_meta.input_ooi,
            bit_id="/bit/port-classification-ip",
            config=json.loads(raw),
        )
