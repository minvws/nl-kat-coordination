from django.db import models
from tools.models import Organization


class PluginDeepLink(models.Model):
    ooi_type = models.CharField(max_length=128, blank=False)
    name = models.CharField(max_length=128, blank=False)
    content = models.CharField(max_length=128, blank=False)
    link = models.URLField(max_length=256, blank=False)

    def __str__(self):
        return self.name


class OrganizationPlugin(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    plugin = models.ForeignKey(PluginDeepLink, on_delete=models.CASCADE)
    enabled = models.BooleanField()

    class Meta:
        unique_together = ["organization", "plugin"]

    def __str__(self):
        return str(self.plugin)
