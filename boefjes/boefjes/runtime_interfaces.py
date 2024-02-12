from enum import Enum
from typing import Dict, List, Tuple, Union

from boefjes.job_models import BoefjeMeta, NormalizerMeta, NormalizerOutput


class Handler:
    def handle(self, item: Union[BoefjeMeta, NormalizerMeta]):
        raise NotImplementedError()


class BoefjeJobRunner:
    def run(self, boefje_meta: BoefjeMeta, environment: Dict[str, str]) -> List[Tuple[set, Union[bytes, str]]]:
        raise NotImplementedError()


class NormalizerJobRunner:
    def run(self, normalizer_meta, raw) -> NormalizerOutput:
        raise NotImplementedError()


class WorkerManager:
    class Queue(Enum):
        BOEFJES = "boefje"
        NORMALIZERS = "normalizer"

    def run(self, queue: Queue) -> None:
        raise NotImplementedError()


class JobRuntimeError(RuntimeError):
    """Base exception class for exceptions raised during running of jobs"""
