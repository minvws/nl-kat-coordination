from typing import Any

from django import template

register = template.Library()


@register.filter
def total_findings(data: dict[str, Any]) -> int:
    total_findings = 0
    for ip in data.values():
        total_findings += int(ip["summary"]["total_findings"])
    return total_findings
