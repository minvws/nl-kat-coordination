from octopoes.models.ooi.service import IPService
from rocky.reports.report_types.definitions import ReportDefinition

REPORT = ReportDefinition(
    name="tls-report",
    required_boefjes=[],
    optional_boefjes=[],
    input_ooi_types={IPService},
    html_template_path="report.html",
)
