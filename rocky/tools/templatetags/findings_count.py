from typing import Any

from django import template

register = template.Library()


@register.filter
def total_findings(data: dict[str, Any]) -> int:
    return sum(int(ip["summary"]["total_findings"]) for ip in data.values())
