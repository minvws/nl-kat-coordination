from datetime import datetime, timezone
from uuid import uuid4

from django.conf import settings
from reports.report_types.aggregate_organisation_report.report import AggregateOrganisationReport
from reports.report_types.findings_report.report import FindingsReport
from reports.report_types.helpers import get_ooi_types_from_aggregate_report
from reports.report_types.systems_report.report import SystemReport
from tools.models import Organization
from tools.ooi_helpers import create_ooi

from crisis_room.models import DashboardData
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import ScanLevel, ScanProfileType
from octopoes.models.ooi.reports import ReportRecipe
from rocky.bytes_client import get_bytes_client
from rocky.scheduler import ReportTask, ScheduleRequest, scheduler_client

PARENT_REPORT = AggregateOrganisationReport
SUB_REPORTS = [SystemReport, FindingsReport]

DEFAULT_OOI_TYPES = {ooi_type.__name__ for ooi_type in get_ooi_types_from_aggregate_report(PARENT_REPORT)}
DEFAULT_SCAN_LEVELS = {ScanLevel.L1, ScanLevel.L2, ScanLevel.L3, ScanLevel.L4}
DEFAULT_SCAN_PROFILES = {ScanProfileType.DECLARED}


def create_dashboard_data(organization: Organization):
    valid_time = datetime.now(timezone.utc)
    is_scheduler_ready_for_schedule = is_scheduler_enabled(organization)

    if is_scheduler_ready_for_schedule:
        recipe = create_organization_recipe(valid_time, organization)
        DashboardData.objects.get_or_create(recipe=recipe.primary_key)
        schedule_request = create_schedule_request(valid_time, organization, recipe)
        scheduler_client(organization.code).post_schedule(schedule=schedule_request)


def create_organization_recipe(valid_time: datetime, organization: Organization) -> ReportRecipe:
    hour = valid_time.hour
    minute = valid_time.minute

    report_recipe = ReportRecipe(
        recipe_id=uuid4(),
        report_name_format="Findings Report for ${oois_count} objects",
        subreport_name_format="Findings Report for ${ooi}",
        input_recipe={
            "query": {
                "ooi_types": DEFAULT_OOI_TYPES,
                "scan_level": DEFAULT_SCAN_LEVELS,
                "scan_type": DEFAULT_SCAN_PROFILES,
                "search_string": "",
                "order_by": "object_type",
                "asc_desc": "desc",
            }
        },
        parent_report_type=PARENT_REPORT.id,
        report_types=[report.id for report in SUB_REPORTS],
        cron_expression=f"{minute} {hour} * * *",
    )

    octopoes_client = OctopoesAPIConnector(
        settings.OCTOPOES_API, organization.code, timeout=settings.ROCKY_OUTGOING_REQUEST_TIMEOUT
    )
    bytes_client = get_bytes_client(organization.code)

    create_ooi(api_connector=octopoes_client, bytes_client=bytes_client, ooi=report_recipe, observed_at=valid_time)
    return report_recipe


def is_scheduler_enabled(organization: Organization) -> bool:
    scheduler_id = f"report-{organization.code}"
    return scheduler_client(organization.code).is_scheduler_ready(scheduler_id)


def create_schedule_request(
    start_datetime: datetime, organization: Organization, report_recipe: ReportRecipe
) -> ScheduleRequest:
    report_task = ReportTask(
        organisation_id=organization.code, report_recipe_id=str(report_recipe.recipe_id)
    ).model_dump()

    return ScheduleRequest(
        scheduler_id=f"report-{organization.code}",
        data=report_task,
        schedule=report_recipe.cron_expression,
        deadline_at=start_datetime.isoformat(),
    )
