from datetime import datetime, timezone
from typing import Any

from django import template
from django.conf import settings
from django.db.models.query import QuerySet
from pydantic import TypeAdapter
from reports.report_types.findings_report.report import SEVERITY_OPTIONS
from tools.models import Organization

from crisis_room.models import DashboardData
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import Reference
from rocky.bytes_client import get_bytes_client

register = template.Library()


def get_octopoes_client(organization: Organization) -> OctopoesAPIConnector:
    return OctopoesAPIConnector(
        settings.OCTOPOES_API, organization.code, timeout=settings.ROCKY_OUTGOING_REQUEST_TIMEOUT
    )


@register.filter()
def get_report_data(dashboard_data: DashboardData) -> dict[str, Any]:
    valid_time = datetime.now(timezone.utc)
    octopoes_client = get_octopoes_client(dashboard_data.dashboard.organization)

    reports = octopoes_client.query(
        "ReportRecipe.<report_recipe[is Report]",
        valid_time=valid_time,
        source=Reference.from_str(dashboard_data.recipe),
    )
    if reports:
        reports.sort(key=lambda ooi: ooi.date_generated, reverse=True)
        report = reports[0]

        bytes_client = get_bytes_client(dashboard_data.dashboard.organization.code)
        bytes_client.login()

        return TypeAdapter(Any, config={"arbitrary_types_allowed": True}).validate_json(
            bytes_client.get_raw(raw_id=report.data_raw_id)
        )
    return {}


@register.filter()
def get_findings_summary(dashboards_data: QuerySet[DashboardData]):
    summary: dict[str, Any] = {
        "total_by_severity": {severity: 0 for severity in SEVERITY_OPTIONS},
        "total_by_severity_per_finding_type": {severity: 0 for severity in SEVERITY_OPTIONS},
        "total_finding_types": 0,
        "total_occurrences": 0,
    }

    for dashboard_data in dashboards_data:
        report_data = get_report_data(dashboard_data)
        if "findings" in report_data:
            for summary_item, data in report_data["findings"]["summary"].items():
                if isinstance(data, dict):
                    for severity, total in data.items():
                        summary[summary_item][severity] += total
                else:
                    summary[summary_item] += data

    return summary
