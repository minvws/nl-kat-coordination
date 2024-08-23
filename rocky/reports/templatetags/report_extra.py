from django import template

from reports.report_types.helpers import get_report_by_id

register = template.Library()


@register.filter
def sum_attribute(checks, attribute):
    return sum(int(check[attribute]) for check in checks)


@register.filter
def get_report_type_name(report_type_id: str):
    return get_report_by_id(report_type_id).name


@register.filter
def get_report_type_label_style(report_type_id: str):
    return get_report_by_id(report_type_id).label_style
