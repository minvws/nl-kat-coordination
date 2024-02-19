from enum import Enum

from boefjes.job_models import BoefjeMeta, NormalizerMeta, NormalizerOutput


class Handler:
    def handle(self, item: BoefjeMeta | NormalizerMeta):
        raise NotImplementedError()


class BoefjeJobRunner:
    def run(self, boefje_meta: BoefjeMeta, environment: dict[str, str]) -> list[tuple[set, bytes | str]]:
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
