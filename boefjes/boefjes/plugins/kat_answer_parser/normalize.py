import logging
from typing import Iterable , Union

from octopoes.models.ooi.config import Config

from boefjes.job_models import NormalizerMeta
from octopoes.models import OOI

logger = logging.getLogger(__name__)


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterable[OOI]:
    yield Config()
