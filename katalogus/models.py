from django.contrib.postgres.fields import ArrayField
from django.db import models

from katalogus.worker.job_models import Boefje as WorkerBoefje
from katalogus.worker.job_models import Normalizer as WorkerNormalizer
from katalogus.worker.models import RunOn
from openkat.models import OrganizationMember


class ScanLevel(models.IntegerChoices):
    L0 = 0
    L1 = 1
    L2 = 2
    L3 = 3
    L4 = 4


class RunOnDB(models.TextChoices):
    CREATE = "create"
    UPDATE = "update"
    CREATE_UPDATE = "create_update"

    @classmethod
    def from_run_ons(cls, run_ons: list[RunOn] | None):
        if run_ons is None:
            return None

        match sorted(run_ons):
            case [RunOn.CREATE]:
                return cls.CREATE
            case [RunOn.UPDATE]:
                return cls.UPDATE
            case [RunOn.CREATE, RunOn.UPDATE]:
                return cls.CREATE_UPDATE
            case _:
                return None

    def to_run_ons(self) -> list[RunOn]:
        match self:
            case RunOnDB.CREATE:
                return [RunOn.CREATE]
            case RunOnDB.UPDATE:
                return [RunOn.UPDATE]
            case RunOnDB.CREATE_UPDATE:
                return [RunOn.CREATE, RunOn.UPDATE]
            case _:
                raise ValueError


class Boefje(models.Model):
    plugin_id = models.CharField(max_length=64, unique=True)
    created = models.DateTimeField(auto_now_add=True)
    static = models.BooleanField(default=False)

    # Metadata
    name = models.CharField(max_length=64, unique=True)
    description = models.TextField(null=True)
    scan_level = models.PositiveSmallIntegerField(choices=ScanLevel.choices, default=ScanLevel.L4)

    # Job specifications
    consumes = ArrayField(models.CharField(max_length=128, blank=True), default=list)
    produces = ArrayField(models.CharField(max_length=128, blank=True), default=list)
    schema = models.JSONField(null=True)
    cron = models.CharField(max_length=128, null=True)
    interval = models.IntegerField(null=True)
    run_on = models.CharField(max_length=16, choices=RunOnDB.choices, null=True)

    # Image specifications
    oci_image = models.CharField(max_length=256, null=True)
    oci_arguments = ArrayField(models.CharField(max_length=128, blank=True), default=list)
    version = models.CharField(max_length=16, null=True)

    def can_scan(self, member: OrganizationMember) -> bool:
        return member.has_perm("openkat.can_scan_organization") and member.has_clearance_level(self.scan_level)

    @property
    def type(self):
        return "boefje"

    def for_task(self) -> WorkerBoefje:
        return WorkerBoefje(
            id=self.id,
            name=self.name,
            plugin_id=self.plugin_id,
            version=self.version,
            oci_image=self.oci_image,
            oci_arguments=self.oci_arguments,
        )


class Normalizer(models.Model):
    plugin_id = models.CharField(max_length=64, unique=True)
    created = models.DateTimeField(auto_now_add=True)
    static = models.BooleanField(default=False)

    # Metadata
    name = models.CharField(max_length=64, unique=True)
    description = models.TextField(null=True)

    # Job specifications
    consumes = ArrayField(models.CharField(max_length=128, blank=True), default=list)
    produces = ArrayField(models.CharField(max_length=128, blank=True), default=list)
    version = models.CharField(max_length=16, null=True)

    @property
    def type(self):
        return "normalizer"

    def can_scan(self, member: OrganizationMember) -> bool:
        return member.has_perm("openkat.can_scan_organization")

    def for_task(self) -> WorkerNormalizer:
        return WorkerNormalizer(
            id=self.id,
            name=self.name,
            created=self.created,
            description=self.description,
            static=self.static,
            plugin_id=self.plugin_id,
            version=self.version,
            consumes=self.consumes,
            produces=self.produces,
        )


class BoefjeConfig(models.Model):
    # TODO: https://pypi.org/project/django-pgcrypto-fields/ ?
    settings = models.CharField(max_length=512, db_default="{}")
    enabled = models.BooleanField(default=False)

    boefje = models.ForeignKey(Boefje, on_delete=models.CASCADE, related_name="boefje_configs")
    organization = models.ForeignKey(
        "openkat.organization", on_delete=models.CASCADE, related_name="boefje_configs", null=True
    )

    class Meta:
        unique_together = ["boefje", "organization"]


class NormalizerConfig(models.Model):
    settings = models.CharField(max_length=512, db_default="{}")
    enabled = models.BooleanField(default=False)

    normalizer = models.ForeignKey(Normalizer, on_delete=models.CASCADE, related_name="normalizer_configs")
    organization = models.ForeignKey(
        "openkat.organization", on_delete=models.CASCADE, related_name="normalizer_configs", null=True
    )

    class Meta:
        unique_together = ["normalizer", "organization"]
