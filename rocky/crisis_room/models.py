from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from tools.models import Organization


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
    recipe = models.CharField(blank=True, max_length=126, null=True)
    query_from = models.CharField(blank=True, max_length=32, null=True)
    query = models.CharField(blank=True, null=True)
    template = models.CharField(blank=True, max_length=126)
    position = models.PositiveSmallIntegerField(
        blank=True,
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
        unique_together = [["dashboard", "position"]]

    def __str__(self) -> str:
        try:
            return str(self.dashboard)
        except Dashboard.DoesNotExist:
            return super().__str__()

    def save(self, *args, **kwargs):
        if not self.position:
            max_position = self.max_position()
            self.position = max_position + 1 if max_position <= 16 else max_position
        super().save(*args, **kwargs)

    def max_position(self):
        return max(DashboardData.objects.filter(dashboard=self.dashboard).values_list("position", flat=True), default=0)
