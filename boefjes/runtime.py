from enum import Enum
from typing import Union

from boefjes.job import BoefjeMeta, NormalizerMeta


class ItemHandler:
    def handle(self, item: Union[BoefjeMeta, NormalizerMeta]):
        raise NotImplementedError()


class RuntimeManager:
    class Queue(Enum):
        BOEFJES = "boefje"
        NORMALIZERS = "normalizer"

    def run(self, queue: Queue) -> None:
        raise NotImplementedError()


class StopWorking(Exception):
    """Exception to tell workers in the runtime to stop working"""
