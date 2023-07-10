import logging
from typing import Iterable, Union

from boefjes.job_models import NormalizerMeta
from octopoes.models import OOI
from octopoes.models.ooi.config import Config

logger = logging.getLogger(__name__)


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterable[OOI]:
    if "/bit/port-classification" in [mime_type["value"] for mime_type in normalizer_meta.raw_data.mime_types]:
        if isinstance(raw, bytes):
            raw = raw.decode()

        yield Config(
            ooi=normalizer_meta.raw_data.boefje_meta.input_ooi, bit_id="/bit/port-classification", config={"ports": raw}
        )
