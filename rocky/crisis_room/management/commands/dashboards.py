import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from crisis_room.models import Dashboard, DashboardData
from django.conf import settings
from django.core.management import BaseCommand
from httpx import HTTPStatusError
from pydantic import ValidationError
from tools.models import Organization
from tools.ooi_helpers import create_ooi

from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models.ooi.reports import ReportRecipe
from rocky.bytes_client import get_bytes_client
from rocky.scheduler import ReportTask, ScheduleRequest, scheduler_client

FINDINGS_DASHBOARD_NAME = "Crisis Room Findings Dashboard"


def get_or_create_default_dashboard(
    organization: Organization, octopoes_client: OctopoesAPIConnector | None = None
) -> bool:
    valid_time = datetime.now(timezone.utc)
    created = False
    path = Path(__file__).parent / "recipe_seeder.json"

    with path.open("r") as recipe_seeder:
        recipe_default = json.load(recipe_seeder)

    dashboard, _ = Dashboard.objects.get_or_create(name=FINDINGS_DASHBOARD_NAME, organization=organization)

    dashboard_data, created = DashboardData.objects.get_or_create(dashboard=dashboard)

    try:
        recipe = create_organization_recipe(octopoes_client, valid_time, organization, recipe_default)
        schedule_request = create_schedule_request(valid_time, organization, recipe)
        scheduler_client(organization.code).post_schedule(schedule=schedule_request)

    except (ValueError, ValidationError, HTTPStatusError, ConnectionError):
        return created

    dashboard_data.recipe = recipe.recipe_id
    dashboard_data.findings_dashboard = True
    dashboard_data.save()

    return created


def create_organization_recipe(
    octopoes_client: OctopoesAPIConnector | None,
    valid_time: datetime,
    organization: Organization,
    recipe_default: dict[str, Any],
) -> ReportRecipe:
    report_recipe = ReportRecipe(recipe_id=uuid4(), **recipe_default)

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
