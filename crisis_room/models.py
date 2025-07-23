from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from openkat.models import Organization


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
    recipe = models.UUIDField(blank=False, null=True)
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
