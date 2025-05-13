from typing import Any

import structlog
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import connection, models, transaction
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from tools.models import Organization

logger = structlog.get_logger(__name__)


class Dashboard(models.Model):
    name = models.CharField(blank=False, max_length=126)
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["name", "organization"]

    def __str__(self) -> str:
        if self.name:
            return f"{self.name} for organization {self.organization}"
        return super().__str__()


MIN_POSITION = 1
MAX_POSITION = 16


def get_default_dashboard_data_settings() -> dict[str, Any]:
    return {"size": "1", "columns": {}}


class DashboardData(models.Model):
    dashboard = models.ForeignKey(Dashboard, on_delete=models.CASCADE, null=True)
    name = models.CharField(blank=True, null=True, max_length=126)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    recipe = models.UUIDField(blank=True, null=True)
    query_from = models.CharField(blank=True, max_length=32, null=True)
    query = models.CharField(blank=True, null=True)
    template = models.CharField(blank=True, max_length=126, default="findings_report/report.html")
    position = models.PositiveSmallIntegerField(
        blank=True,
        validators=[MinValueValidator(MIN_POSITION), MaxValueValidator(MAX_POSITION)],
        help_text=_(
            "Where on the dashboard do you want to show the data? "
            "Position {} is the most top level and the max position is {}."
        ).format(MIN_POSITION, MAX_POSITION),
    )
    settings = models.JSONField(blank=True, null=True, default=get_default_dashboard_data_settings)
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
        permissions = ("can_change_dashboard_item_position", _("Can change dashboard item position"))
        constraints = [
            models.UniqueConstraint(
                name="unique dashboard position",
                fields=["dashboard", "position"],
                deferrable=models.Deferrable.DEFERRED,
            ),
            models.UniqueConstraint(
                name="unique dashboard name", fields=["dashboard", "name"], deferrable=models.Deferrable.DEFERRED
            ),
        ]

    def __str__(self) -> str:
        try:
            return str(self.dashboard)
        except Dashboard.DoesNotExist:
            return super().__str__()

    def clean(self) -> None:
        if self.recipe and self.query:
            raise ValidationError(_("You have to choose between a recipe or a query, but not both."))
        if self.query and not self.query_from:
            raise ValidationError(_("You have set a query and not where it is from. Also set the query_from."))
        if not self.recipe and not self.query_from and not self.query:
            raise ValidationError(_("DashboardData must contain at least a 'recipe' or a 'query_from' with a 'query'."))
        return super().clean()

    def update_position(self, move: str) -> None:
        if move not in ("up", "down"):
            return

        old_position = self.position
        new_position = self.position + (-1 if move == "up" else 1)

        if 1 <= new_position <= 16:
            try:
                swap_item = DashboardData.objects.get(dashboard=self.dashboard, position=new_position)

                # Swap positions and temporarily change position to 0 to avoid conflicts
                with transaction.atomic():
                    self.position = 0
                    self.save(update_fields=["position"])
                    swap_item.position = old_position
                    swap_item.save(update_fields=["position"])
                    self.position = new_position
                    self.save(update_fields=["position"])
            except DashboardData.DoesNotExist:
                return


def get_dashboard_data_positions(instance: DashboardData) -> list[int]:
    return list(DashboardData.objects.filter(dashboard=instance.dashboard).values_list("position", flat=True))


@receiver(pre_save, sender=DashboardData)
def dashboard_data_pre_save(sender, instance, *args, **kwargs):
    if instance._state.adding:  # not when updating
        positions = get_dashboard_data_positions(instance)
        position = max(positions, default=0) + 1
        if position <= MAX_POSITION:
            instance.position = position
        else:
            raise ValidationError(_("Max dashboard items reached."))


@receiver(post_delete, sender=DashboardData)
def dashboard_data_post_delete(sender, instance, *args, **kwargs):
    """Change the position of the other items on the dashboard after deleting one object."""
    position = instance.position
    dashboard = instance.dashboard_id
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE crisis_room_dashboarddata "
            "SET position = position - 1 "
            "WHERE position > %s "
            "AND dashboard_id = %s ",
            [position, dashboard],
        )
