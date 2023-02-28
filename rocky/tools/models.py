import logging
import uuid

import tagulous.models
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.signals import post_save
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from katalogus.client import get_katalogus
from octopoes.connector.octopoes import OctopoesAPIConnector
from rocky.exceptions import RockyError
from tools.add_ooi_information import get_info, SEPARATOR
from tools.enums import SCAN_LEVEL
from tools.fields import LowerCaseSlugField

User = get_user_model()

GROUP_ADMIN = "admin"
GROUP_REDTEAM = "redteam"
GROUP_CLIENT = "clients"

logger = logging.getLogger(__name__)

ORGANIZATION_CODE_LENGTH = 32


class OrganizationTag(tagulous.models.TagTreeModel):
    COLOR_CHOICES = settings.TAG_COLORS
    BORDER_TYPE_CHOICES = settings.TAG_BORDER_TYPES

    color = models.CharField(choices=COLOR_CHOICES, max_length=20, default=COLOR_CHOICES[0][0])
    border_type = models.CharField(choices=BORDER_TYPE_CHOICES, max_length=20, default=BORDER_TYPE_CHOICES[0][0])

    class TagMeta:
        force_lowercase = True
        protect_all = True

    @property
    def css_class(self):
        return f"tags-{self.color} {self.border_type}"


class Organization(models.Model):
    name = models.CharField(max_length=126, unique=True, help_text=_("The name of the organisation"))
    code = LowerCaseSlugField(
        max_length=ORGANIZATION_CODE_LENGTH,
        unique=True,
        allow_unicode=True,
        help_text=_(
            "A slug containing only lower-case unicode letters, numbers, hyphens or underscores "
            "that will be used in URLs and paths"
        ),
    )
    tags = tagulous.models.TagField(to=OrganizationTag, blank=True)

    def __str__(self):
        return str(self.name)

    class Meta:
        permissions = (
            ("can_switch_organization", "Can switch organization"),
            ("can_scan_organization", "Can scan organization"),
            ("can_enable_disable_boefje", "Can enable or disable boefje"),
            ("can_set_clearance_level", "Can set clearance level"),
        )

    def get_absolute_url(self):
        return reverse("organization_detail", args=[self.pk])

    def delete(self, *args, **kwargs):
        katalogus_client = get_katalogus(self.code)
        try:
            katalogus_client.delete_organization()
        except Exception as e:
            raise RockyError(f"Katalogus returned error deleting organization: {e}") from e

        octopoes_client = OctopoesAPIConnector(settings.OCTOPOES_API, client=self.code)
        try:
            octopoes_client.delete_node()
        except Exception as e:
            raise RockyError(f"Octopoes returned error deleting organization: {e}") from e

        super().delete(*args, **kwargs)

    @classmethod
    def post_create(cls, sender, instance, created, *args, **kwargs):
        if not created:
            return

        katalogus_client = get_katalogus(instance.code)

        try:
            if not katalogus_client.organization_exists():
                katalogus_client.create_organization(instance.name)
        except Exception as e:
            raise RockyError(f"Katalogus returned error creating organization: {e}") from e

        octopoes_client = OctopoesAPIConnector(settings.OCTOPOES_API, client=instance.code)

        try:
            octopoes_client.create_node()
        except Exception as e:
            raise RockyError(f"Octopoes returned error creating organization: {e}") from e


post_save.connect(Organization.post_create, sender=Organization)


class OrganizationMember(models.Model):
    class STATUSES(models.TextChoices):
        ACTIVE = "active", _("active")
        NEW = "new", _("new")
        BLOCKED = "blocked", _("blocked")

    scan_levels = [scan_level.value for scan_level in SCAN_LEVEL]

    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True, related_name="members")
    verified = models.BooleanField(default=False)
    authorized = models.BooleanField(default=False)
    status = models.CharField(choices=STATUSES.choices, max_length=64, default=STATUSES.NEW)
    member_name = models.CharField(max_length=126)
    onboarded = models.BooleanField(default=False)
    trusted_clearance_level = models.IntegerField(
        default=-1, validators=[MinValueValidator(-1), MaxValueValidator(max(scan_levels))]
    )
    acknowledged_clearance_level = models.IntegerField(
        default=-1, validators=[MinValueValidator(-1), MaxValueValidator(max(scan_levels))]
    )

    class Meta:
        unique_together = ["user", "organization"]

    def __str__(self):
        return str(self.user)


class Indemnification(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True)


class OOIInformation(models.Model):
    id = models.CharField(max_length=256, primary_key=True)
    last_updated = models.DateTimeField(auto_now=True)
    data = models.JSONField(null=True)
    consult_api = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.data is None:
            self.data = {"description": ""}
        if self.consult_api:
            self.consult_api = False
            self.get_internet_description()
        super(OOIInformation, self).save(*args, **kwargs)

    def clean(self):
        if "description" not in self.data:
            raise ValidationError("Description is missing in data")

    @property
    def type(self):
        return self.id.split(SEPARATOR)[0]

    @property
    def value(self):
        return SEPARATOR.join(self.id.split(SEPARATOR)[1:])

    @property
    def description(self):
        if self.data["description"] == "":
            self.get_internet_description()
        return self.data["description"]

    def get_internet_description(self):
        for key, value in get_info(ooi_type=self.type, natural_key=self.value).items():
            self.data[key] = value
        self.save()

    def __str__(self):
        return self.id


class Job(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True)
    boefje_id = models.CharField(max_length=128)
    input_ooi = models.TextField(null=True)
    arguments = models.JSONField()
    created = models.DateTimeField(auto_now_add=True)
