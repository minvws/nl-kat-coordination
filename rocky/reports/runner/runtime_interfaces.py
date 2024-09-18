from enum import Enum

from octopoes.models.ooi.reports import ReportRecipe


class ReportJobRunner:
    def run(self, recipe: ReportRecipe) -> list[tuple[set, bytes | str]]:
        raise NotImplementedError()


class WorkerManager:
    class Queue(Enum):
        REPORTS = "report"

    def run(self, queue: Queue) -> None:
        raise NotImplementedError()


class JobRuntimeError(RuntimeError):
    """Base exception class for exceptions raised during running of jobs"""
