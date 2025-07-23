from pydantic import BaseModel

from octopoes.models.ooi.reports import ReportRecipe


class ReportTask(BaseModel):
    """ReportTask represent data needed for a Report to run."""

    type: str = "report"

    organisation_id: str
    report_recipe_id: str


class ReportRunner:
    def run(self, recipe: ReportRecipe) -> None:
        raise NotImplementedError()


class JobRuntimeError(RuntimeError):
    """Base exception class for exceptions raised during running of jobs"""
