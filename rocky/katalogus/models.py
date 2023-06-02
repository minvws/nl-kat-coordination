from django.db import models
from django.utils.translation import gettext_lazy as _
from tools.models import Organization


class PluginDeepLink(models.Model):
    ooi_type = models.CharField(max_length=128, blank=False)
    name = models.CharField(max_length=128, blank=False)
    content = models.CharField(max_length=128, blank=False)
    link = models.URLField(max_length=256, blank=False)

    class Meta:
        unique_together = ["ooi_type", "name"]

    def unique_error_message(self, model_class, unique_check):
        if model_class == type(self) and unique_check == ("ooi_type", "name"):
            return _("This plugin already exists. Choose another name or OOI-Type.")
        else:
            return super().unique_error_message(model_class, unique_check)

    def __str__(self):
        return self.name


class OrganizationPlugin(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    plugin = models.ForeignKey(PluginDeepLink, on_delete=models.CASCADE)
    enabled = models.BooleanField()

    class Meta:
        unique_together = ["organization", "plugin"]

    def unique_error_message(self, model_class, unique_check):
        if model_class == type(self) and unique_check == ("organization", "plugin"):
            return _("This plugin already exists. Choose another organization or plugin.")
        else:
            return super().unique_error_message(model_class, unique_check)

    def __str__(self):
        return str(self.plugin)
