from typing import Iterable, Union

from boefjes.job_models import NormalizerMeta
from octopoes.models import OOI, Reference


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterable[OOI]:
    boefje_meta = normalizer_meta.raw_data.boefje_meta
    Reference.from_str(boefje_meta.input_ooi)
