from datetime import datetime, timezone
from uuid import uuid4

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from reports.report_types.aggregate_organisation_report.report import AggregateOrganisationReport
from reports.report_types.findings_report.report import FindingsReport
from reports.report_types.helpers import get_ooi_types_with_report
from tools.models import Organization
from tools.ooi_helpers import create_ooi

from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import ScanLevel, ScanProfileType
from octopoes.models.ooi.reports import ReportRecipe
from rocky.bytes_client import get_bytes_client
from rocky.scheduler import ReportTask, ScheduleRequest, scheduler_client

DEFAULT_OOI_TYPES = [ooi_type.__name__ for ooi_type in get_ooi_types_with_report()]
DEFAULT_SCAN_LEVELS = {ScanLevel.L2}
DEFAULT_SCAN_PROFILES = {ScanProfileType.EMPTY, ScanProfileType.INHERITED, ScanProfileType.DECLARED}
PARENT_REPORT = AggregateOrganisationReport
SUB_REPORT = FindingsReport


class Dashboard(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True)
    recipe = models.CharField(
        blank=True,
        max_length=126,
        unique=True,
        help_text=_(
            "The recipe will be automatically created once you create a dashboard for an organization. "
            "This is the recipe id."
        ),
    )

    class Meta:
        unique_together = ["organization", "recipe"]

    def save(self, *args, **kwargs):
        if not self.recipe and self.organization:
            self.create_dashboard(self.organization)
        super().save(*args, **kwargs)

    def get_readonly_fields(self, request, obj=None):
        return ["recipe"]

    def is_scheduler_ready(self, organization: Organization) -> bool:
        scheduler_id = f"report-{organization.code}"
        return scheduler_client(organization.code).is_scheduler_ready(scheduler_id)

    @staticmethod
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
            report_types=[SUB_REPORT.id],
            cron_expression=f"{minute} {hour} * * *",
        )

        octopoes_client = OctopoesAPIConnector(
            settings.OCTOPOES_API, organization.code, timeout=settings.ROCKY_OUTGOING_REQUEST_TIMEOUT
        )
        bytes_client = get_bytes_client(organization.code)

        create_ooi(api_connector=octopoes_client, bytes_client=bytes_client, ooi=report_recipe, observed_at=valid_time)
        return report_recipe

    def create_schedule_request(
        self, start_datetime: datetime, organization: Organization, report_recipe: ReportRecipe
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

    def create_dashboard(self, organization: Organization):
        valid_time = datetime.now(timezone.utc)
        is_scheduler_ready = self.is_scheduler_ready(organization)

        if is_scheduler_ready:
            recipe = self.create_organization_recipe(valid_time, organization)
            self.recipe = recipe.primary_key
            schedule_request = self.create_schedule_request(valid_time, organization, recipe)
            scheduler_client(organization.code).post_schedule(schedule=schedule_request)

    def __str__(self) -> str:
        if self.organization:
            return self.organization.name
        return super().__str__()
