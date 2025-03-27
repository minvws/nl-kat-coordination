import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from crisis_room.models import Dashboard, DashboardData
from django.conf import settings
from django.core.management import BaseCommand
from tools.models import Organization
from tools.ooi_helpers import create_ooi

from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models.ooi.reports import ReportRecipe
from rocky.bytes_client import get_bytes_client
from rocky.scheduler import ReportTask, ScheduleRequest, scheduler_client

FINDINGS_DASHBOARD_NAME = "Crisis Room Findings Dashboard"
FINDINGS_DASHBOARD_TEMPLATE = "findings_report/report.html"


def get_or_create_default_dashboard(
    organization: Organization, octopoes_client: OctopoesAPIConnector | None = None
) -> bool:
    created = False
    path = Path(__file__).parent / "recipe_seeder.json"

    with path.open("r") as recipe_seeder:
        recipe_default = json.load(recipe_seeder)

    dashboard, _ = Dashboard.objects.get_or_create(name=FINDINGS_DASHBOARD_NAME, organization=organization)
    dashboard_data, created = DashboardData.objects.get_or_create(
        dashboard=dashboard, template=FINDINGS_DASHBOARD_TEMPLATE
    )

    if created:
        report_recipe = ReportRecipe(recipe_id=uuid4(), **recipe_default)
        schedule_recipe(dashboard_data, organization, octopoes_client, report_recipe)

    dashboard_data.findings_dashboard = True
    dashboard_data.display_in_dashboard = True
    dashboard_data.save()
    return created


def get_or_create_dashboard(dashboard_name: str, organization: Organization,) -> tuple[Dashboard, bool]:
    dashboard, created = Dashboard.objects.get_or_create(name=dashboard_name, organization=organization)
    return dashboard, created 


def get_or_create_dashboard_data(
    dashboard_name: str, organization: Organization, recipe_id: str, query_from: str, query: dict, template: str
) -> tuple[DashboardData | None, bool]:
    dashboard, _ = get_or_create_dashboard(dashboard_name, organization)
    
    dashboard_data = None
    if recipe_id or query_from:
        dashboard_data, created = DashboardData.objects.get_or_create(
            dashboard=dashboard, recipe=recipe_id, query_from=query_from, query=json.dumps(query), template=template
        )
        dashboard_data.display_in_dashboard = True
        dashboard_data.save()
    return dashboard_data, created


def schedule_recipe(
    dashboard_data: DashboardData,
    organization: Organization,
    octopoes_client: OctopoesAPIConnector,
    report_recipe: ReportRecipe,
):
    valid_time = datetime.now(timezone.utc)
    recipe = create_organization_recipe(octopoes_client, valid_time, organization, report_recipe)
    dashboard_data.recipe = recipe.recipe_id
    schedule_request = create_schedule_request(valid_time, organization, recipe)
    scheduler_client(organization.code).post_schedule(schedule=schedule_request)


def create_organization_recipe(
    octopoes_client: OctopoesAPIConnector | None,
    valid_time: datetime,
    organization: Organization,
    report_recipe: ReportRecipe,
) -> ReportRecipe:
    if octopoes_client is None:
        octopoes_client = OctopoesAPIConnector(
            settings.OCTOPOES_API, organization.code, timeout=settings.ROCKY_OUTGOING_REQUEST_TIMEOUT
        )

    bytes_client = get_bytes_client(organization.code)

    create_ooi(api_connector=octopoes_client, bytes_client=bytes_client, ooi=report_recipe, observed_at=valid_time)
    return report_recipe


def create_schedule_request(
    start_datetime: datetime, organization: Organization, report_recipe: ReportRecipe
) -> ScheduleRequest:
    report_task = ReportTask(
        organisation_id=organization.code, report_recipe_id=str(report_recipe.recipe_id)
    ).model_dump()

    return ScheduleRequest(
        scheduler_id="report",
        organisation=organization.code,
        data=report_task,
        schedule=report_recipe.cron_expression,
        deadline_at=start_datetime.isoformat(),
    )


class Command(BaseCommand):
    def handle(self, *args, **options):
        organizations = Organization.objects.all()
        for organization in organizations:
            created = get_or_create_default_dashboard(organization)
            if created:
                logging.info("Dashboard created for organization %s", organization.name)
