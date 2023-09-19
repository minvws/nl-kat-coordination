from octopoes.models.ooi.dns.zone import Hostname
from rocky.reports.report_types.definitions import ReportDefinition

REPORT = ReportDefinition(
    name="dns-report",
    required_boefjes=[],
    optional_boefjes=[],
    input_ooi_types={Hostname},
    html_template_path="report.html",
)
