from django.db import models
from django.utils.translation import gettext_lazy as _
from tools.models import Organization


class DashboardData(models.Model):
    recipe = models.CharField(
        blank=True,
        max_length=126,
        unique=True,
        help_text=_(
            "The recipe will be automatically created once you create a dashboard for an organization. "
            "This is the recipe id."
        ),
    )
    chapter = models.CharField(blank=True, max_length=126)
    sort = models.CharField(blank=True, max_length=126)

    def get_readonly_fields(self, request, obj=None):
        return ["recipe"]


class Dashboard(models.Model):
    name = models.CharField(blank=False, max_length=126, unique=True)
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True)
    data = models.ForeignKey(DashboardData, on_delete=models.SET_NULL, null=True)

    def __str__(self) -> str:
        if self.name:
            return self.name
        return super().__str__()
