import recurrence.fields
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import Q, UniqueConstraint

from openkat.models import OrganizationMember


class ScanLevel(models.IntegerChoices):
    L0 = 0
    L1 = 1
    L2 = 2
    L3 = 3
    L4 = 4


class Plugin(models.Model):
    plugin_id = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)  # TODO: updated_at?

    # Metadata
    name = models.CharField(max_length=64, unique=True)
    description = models.TextField(null=True)
    scan_level = models.PositiveSmallIntegerField(choices=ScanLevel.choices, default=ScanLevel.L4)

    # Task specifications
    consumes = ArrayField(models.CharField(max_length=128, blank=True), default=list)  # TODO: revise
    recurrences = recurrence.fields.RecurrenceField(null=True)

    # Image specifications
    oci_image = models.CharField(max_length=256, null=True)
    oci_arguments = ArrayField(models.CharField(max_length=128, blank=True), default=list)
    version = models.CharField(max_length=16, null=True)


class PluginSettings(models.Model):
    settings = models.JSONField(default=dict)  # TODO: encoder/decoder with for datatimes?
    plugin = models.ForeignKey(Plugin, on_delete=models.CASCADE, related_name="plugin_settings")
    organizations = models.ManyToManyField("openkat.organization", related_name="plugin_settings")


class EnabledPlugin(models.Model):
    enabled = models.BooleanField(default=False)
    plugin = models.ForeignKey(Plugin, on_delete=models.CASCADE, related_name="enabled_plugins")
    organization = models.ForeignKey(
        "openkat.organization", on_delete=models.CASCADE, related_name="enabled_plugins", null=True, blank=True
    )

    class Meta:
        constraints = [
            UniqueConstraint(fields=["plugin", "organization"], name="unique_enabled_per_organization"),
            UniqueConstraint(fields=["plugin"], condition=Q(organization=None), name="unique_global_enabled"),
        ]

    def can_scan(self, member: OrganizationMember) -> bool:
        return member.has_perm("openkat.can_scan_organization")
