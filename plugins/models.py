import datetime
from datetime import timezone

import recurrence
import structlog
from django.contrib.postgres.fields import ArrayField
from django.db import DatabaseError, models
from django.db.models import Case, F, OuterRef, Q, QuerySet, Subquery, UniqueConstraint, When
from docker.utils import parse_repository_tag
from recurrence.fields import RecurrenceField

from objects.models import ObjectSet
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.network import IPAddress, IPAddressV4, IPAddressV6
from octopoes.models.types import ALL_TYPES_MAP
from openkat.models import Organization, OrganizationMember
from tasks.models import NewSchedule

logger = structlog.get_logger(__name__)


class ScanLevel(models.IntegerChoices):
    L0 = 0
    L1 = 1
    L2 = 2
    L3 = 3
    L4 = 4


class PluginQuerySet(models.QuerySet):
    def with_enabled(self, organization: Organization | None):
        global_subquery = EnabledPlugin.objects.filter(Q(organization=None), plugin=OuterRef("pk"))
        subquery = EnabledPlugin.objects.filter(Q(organization=organization), plugin=OuterRef("pk"))

        qs = self.annotate(
            global_enabled=Subquery(global_subquery.values("enabled")),
            global_enabled_id=Subquery(global_subquery.values("pk")),
            specific_enabled=Subquery(subquery.values("enabled")),
            specific_enabled_id=Subquery(subquery.values("pk")),
        ).annotate(
            enabled=Case(
                When(specific_enabled__isnull=False, then=F("specific_enabled")),
                When(global_enabled__isnull=False, then=F("global_enabled")),
                default=False,
            ),
            enabled_id=Case(
                When(specific_enabled_id__isnull=False, then=F("specific_enabled_id")),
                When(global_enabled_id__isnull=False, then=F("global_enabled_id")),
            ),
        )

        return qs


class Plugin(models.Model):
    plugin_id = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)  # TODO: updated_at?

    # Metadata
    name = models.CharField(max_length=64, unique=True)
    description = models.TextField(null=True, blank=True)
    scan_level = models.PositiveSmallIntegerField(choices=ScanLevel.choices, default=ScanLevel.L4)

    # Task specifications
    consumes = ArrayField(models.CharField(max_length=128, blank=True), default=list)  # TODO: revise
    recurrences = RecurrenceField(null=True, blank=True)  # If set, this is used as a default

    # Image specifications
    oci_image = models.CharField(max_length=256, null=True)
    oci_arguments = ArrayField(models.CharField(max_length=256, blank=True), default=list)
    version = models.CharField(max_length=16, null=True)

    objects = PluginQuerySet.as_manager()

    def repository(self) -> str | None:
        if not self.oci_arguments:
            return None

        repository, tag = parse_repository_tag(self.oci_image)

        return repository

    def real_version(self) -> str | None:
        if self.version:
            return self.version

        if not self.oci_arguments:
            return None

        repository, tag = parse_repository_tag(self.oci_image)
        # Note: to resolve to the registry, use resolve_repository_name(repository)

        return tag or "latest"

    def types_in_arguments(self):
        return list(
            {
                ALL_TYPES_MAP[part]
                for arg in self.oci_arguments
                if arg.startswith("{") and arg.endswith("}")
                for part in arg[1:-1].lower().split("|")
                if part in ALL_TYPES_MAP
            }
        )

    def consumed_types(self):
        return list(
            {
                ALL_TYPES_MAP[part]
                for arg in self.oci_arguments
                if arg.startswith("{") and arg.endswith("}")
                for part in arg[1:-1].lower().split("|")
                if part in ALL_TYPES_MAP
            }
        ) + [ALL_TYPES_MAP[consume.lstrip("type:")] for consume in self.consumes if consume.startswith("type:") and consume.lstrip("type:") in ALL_TYPES_MAP]

    def enabled_organizations(self) -> QuerySet:
        orgs = Organization.objects.filter(enabled_plugins__plugin=self, enabled_plugins__enabled=True)

        if not self.enabled_plugins.filter(organization=None, enabled=True).exists():
            return orgs

        # This plugin is globally enabled
        return orgs.union(Organization.objects.difference(Organization.objects.filter(enabled_plugins__plugin=self)))

    def enabled_for(self, organization: Organization | None) -> bool:
        enabled_plugin = self.enabled_plugins.filter(organization=organization).first()

        if enabled_plugin:
            return enabled_plugin.enabled

        enabled_plugin = self.enabled_plugins.filter(organization=None).first()

        if enabled_plugin:
            return enabled_plugin.enabled

        return False

    def enable(self) -> "EnabledPlugin":
        return self.enable_for(None)

    def disable(self) -> "EnabledPlugin":
        return self.disable_for(None)

    def enable_for(self, organization: Organization | None) -> "EnabledPlugin":
        enabled_plugin, created = EnabledPlugin.objects.get_or_create(plugin=self, organization=organization)
        enabled_plugin.enabled = True
        enabled_plugin.save()

        return enabled_plugin

    def disable_for(self, organization: Organization | None) -> "EnabledPlugin":
        enabled_plugin, created = EnabledPlugin.objects.get_or_create(plugin=self, organization=organization)
        enabled_plugin.enabled = False
        enabled_plugin.save()

        return enabled_plugin

    def __str__(self):
        return f"{self.plugin_id}"


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

    def save(self, *args, **kwargs):
        if self.enabled:
            try:
                self.initialize_schedules()
            except DatabaseError:
                logger.warning("Could not aligns schedules for plugin: %s", self)
                raise

        return super().save(*args, **kwargs)

    def initialize_schedules(self):
        schedules = NewSchedule.objects.filter(plugin=self.plugin, organization=self.organization)

        if schedules.exists():
            return

        queries = []

        # TODO: once moved to XTDB 2.0 we can revise this
        for ooi_type in self.plugin.consumed_types():
            if ooi_type == Hostname:
                queries.append(("Hostname.name", "All hostnames"))
            if ooi_type in [IPAddressV4, IPAddressV6, IPAddress]:
                queries.append((f"{ooi_type.get_object_type()}.address", "All IPs"))

        # So this is possibly the first time enabling the plugin for the organization
        for query, name in queries:
            object_set = ObjectSet.objects.create(name=name, object_query=query, dynamic=True)
            NewSchedule.objects.create(
                plugin=self.plugin,
                enabled=self.enabled,
                object_set=object_set,
                organization=self.organization,
                recurrences=self.plugin.recurrences
                if self.plugin.recurrences and str(self.plugin.recurrences)
                else recurrence.Recurrence(
                    rrules=[recurrence.Rule(recurrence.DAILY)],  # Daily scheduling is the default for plugins
                    dtstart=datetime.datetime.now(timezone.utc),
                ),
            )

        if not queries:
            logger.info("not on")

            NewSchedule.objects.create(
                plugin=self.plugin,
                enabled=self.enabled,
                organization=self.organization,
                recurrences=self.plugin.recurrences
                if self.plugin.recurrences and str(self.plugin.recurrences)
                else recurrence.Recurrence(
                    rrules=[recurrence.Rule(recurrence.DAILY)], dtstart=datetime.datetime.now(timezone.utc)
                ),
            )
