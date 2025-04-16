import structlog
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from tools.models import Organization

logger = structlog.get_logger(__name__)


class Dashboard(models.Model):
    name = models.CharField(blank=False, max_length=126)
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True)

    class Meta:
        unique_together = ["name", "organization"]

    def __str__(self) -> str:
        if self.name:
            return f"{self.name} for organization {self.organization}"
        return super().__str__()


class DashboardData(models.Model):
    dashboard = models.ForeignKey(Dashboard, on_delete=models.CASCADE, null=True)
    name = models.CharField(blank=True, null=True, max_length=126)
    recipe = models.UUIDField(blank=True, null=True)
    query_from = models.CharField(blank=True, max_length=32, null=True)
    query = models.CharField(blank=True, null=True)  # TODO: change to JSON
    template = models.CharField(blank=True, max_length=126, default="findings_report/report.html")
    position = models.PositiveSmallIntegerField(
        blank=True,
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(16)],
        help_text=_(
            "Where on the dashboard do you want to show the data? "
            "Position 1 is the most top level and the max position is 16."
        ),
    )
    settings = models.CharField(blank=True, null=True)  # TODO: change to JSON
    display_in_crisis_room = models.BooleanField(
        default=False, help_text=_("Will be displayed on the general crisis room, for all organizations.")
    )
    display_in_dashboard = models.BooleanField(
        default=False, help_text=_("Will be displayed on a single organization dashboard")
    )
    findings_dashboard = models.BooleanField(
        default=False, help_text=_("Will be displayed on the findings dashboard for all organizations")
    )

    class Meta:
        unique_together = [["dashboard", "position"], ["dashboard", "findings_dashboard"]]

    def __str__(self) -> str:
        try:
            return str(self.dashboard)
        except Dashboard.DoesNotExist:
            return super().__str__()

    def save(self, *args, **kwargs):
        try:
            if not self.recipe:
                if not self.query_from and not self.query:
                    raise ValidationError(
                        _("DashboardData must contain at least a 'recipe' or a 'query_from' with a 'query'.")
                    )
                if self.query_from != "object_list":
                    raise ValidationError(_("Empty field 'query_from'. Value should be 'object_list'."))
                elif not self.query:
                    raise ValidationError(_("Empty field 'query'."))

            if not self.position:
                max_position = self.max_position()
                if max_position <= 16:
                    self.position = max_position + 1
                else:
                    raise ValidationError(_("The maximum of 16 dashboard items has been reached."))
            super().save(*args, **kwargs)
        except ValidationError as e:
            logger.error("ValidationError: %s", e)

    def max_position(self):
        return max(DashboardData.objects.filter(dashboard=self.dashboard).values_list("position", flat=True), default=0)
