from octopoes.models.ooi.reports import ReportRecipe
from reports.runner.runtime_interfaces import ReportJobRunner


class LocalReportJobRunner(ReportJobRunner):
    def run(self, recipe: ReportRecipe) -> list[tuple[set, bytes | str]]:
        # generate_report()
        pass
