from django import template

from reports.report_types.helpers import AGGREGATE_REPORTS, MULTI_REPORTS, REPORTS

register = template.Library()


@register.filter
def report_name_by_id(report_id: str):
    for report in REPORTS + MULTI_REPORTS + AGGREGATE_REPORTS:
        if report.id == report_id:
            return report.name
