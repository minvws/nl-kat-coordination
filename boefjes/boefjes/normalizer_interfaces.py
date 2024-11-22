from boefjes.job_models import NormalizerMeta
from boefjes.normalizer_models import NormalizerResults


class NormalizerJobRunner:
    def run(self, normalizer_meta: NormalizerMeta, raw: bytes) -> NormalizerResults:
        raise NotImplementedError()
