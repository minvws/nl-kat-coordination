import datetime
import logging
from functools import cached_property
from typing import Iterable, Set

import tagulous.models
from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.signals import pre_save, post_save
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from katalogus.client import KATalogusClientV1, get_katalogus
from katalogus.exceptions import (
    KATalogusDownException,
    KATalogusException,
    KATalogusUnhealthyException,
)
from requests import RequestException

from octopoes.api.models import Declaration
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models.ooi.web import Network
from rocky.exceptions import (
    OctopoesDownException,
    OctopoesException,
    OctopoesUnhealthyException,
)
from tools.add_ooi_information import SEPARATOR, get_info
from tools.enums import SCAN_LEVEL
from tools.fields import LowerCaseSlugField

GROUP_ADMIN = "admin"
GROUP_REDTEAM = "redteam"
GROUP_CLIENT = "clients"

logger = logging.getLogger(__name__)

ORGANIZATION_CODE_LENGTH = 32
DENY_ORGANIZATION_CODES = [
    "admin",
    "api",
    "i18n",
    "health",
    "privacy-statement",
    "account",
    "crisis-room",
    "onboarding",
    "indemnifications",
    "findings",
    "objects",
    "organizations",
    "edit",
    "members",
    "settings",
    "scans",
    "upload",
    "tasks",
    "bytes",
    "kat-alogus",
    "boefjes",
    "mula",
    "keiko",
    "octopoes",
    "rocky",
    "fmea",
]


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
            ("can_delete_oois", "Can delete oois"),
            ("can_mute_findings", "Can mute findings"),
            ("can_view_katalogus_settings", "Can view KAT-alogus settings"),
            ("can_set_katalogus_settings", "Can set KAT-alogus settings"),
            ("can_recalculate_bits", "Can recalculate bits"),
        )

    def get_absolute_url(self):
        return reverse("organization_settings", args=[self.pk])

    def delete(self, *args, **kwargs):
        katalogus_client = self._get_healthy_katalogus(self.code)
        octopoes_client = self._get_healthy_octopoes(self.code)

        try:
            octopoes_client.delete_node()
        except Exception as e:
            raise OctopoesException("Failed deleting organization in Octopoes") from e

        try:
            katalogus_client.delete_organization()
        except Exception as e:
            try:
                octopoes_client.create_node()
            except Exception as e:
                raise OctopoesException("Failed creating organization in Octopoes") from e

            raise KATalogusException("Failed deleting organization in the Katalogus") from e

        super().delete(*args, **kwargs)

    def clean(self):
        if self.code in DENY_ORGANIZATION_CODES:
            raise ValidationError(
                {
                    "code": _(
                        "This organization code is reserved by OpenKAT and cannot be used. "
                        "Choose another organization code."
                    )
                }
            )

    @classmethod
    def pre_create(cls, sender, instance, *args, **kwargs):
        instance.clean()
        katalogus_client = cls._get_healthy_katalogus(instance.code)
        octopoes_client = cls._get_healthy_octopoes(instance.code)

        try:
            if not katalogus_client.organization_exists():
                katalogus_client.create_organization(instance.name)
        except Exception as e:
            raise KATalogusException("Failed creating organization in the Katalogus") from e

        try:
            octopoes_client.create_node()
        except Exception as e:
            try:
                katalogus_client.delete_organization()
            except Exception as e:
                raise KATalogusException("Failed deleting organization in the Katalogus") from e

            raise OctopoesException("Failed creating organization in Octopoes") from e

    @classmethod
    def post_create(cls, sender, instance, *args, **kwargs):
        octopoes_client = cls._get_healthy_octopoes(instance.code)

        try:
            valid_time = datetime.datetime.now(datetime.timezone.utc)
            octopoes_client.save_declaration(Declaration(ooi=Network(name="internet"), valid_time=valid_time))
        except Exception as e:
            logger.exception(f"Could not seed internet for organization {sender}")

    @staticmethod
    def _get_healthy_katalogus(organization_code: str) -> KATalogusClientV1:
        katalogus_client = get_katalogus(organization_code)

        try:
            health = katalogus_client.health()
        except RequestException as e:
            raise KATalogusDownException from e

        if not health.healthy:
            raise KATalogusUnhealthyException

        return katalogus_client

    @staticmethod
    def _get_healthy_octopoes(organization_code: str) -> OctopoesAPIConnector:
        octopoes_client = OctopoesAPIConnector(settings.OCTOPOES_API, client=organization_code)
        try:
            health = octopoes_client.root_health()
        except RequestException as e:
            raise OctopoesDownException from e

        if not health.healthy:
            raise OctopoesUnhealthyException

        return octopoes_client


pre_save.connect(Organization.pre_create, sender=Organization)
post_save.connect(Organization.post_create, sender=Organization)


class OrganizationMember(models.Model):
    # New is the status after an e-mail invite has been created for a member but the invite hasn't been accepted yet.
    # Active is when the member has accepted the invited or the account was created directly without an invite.
    # Blocked is when an organization admin has blocked the member.
    class STATUSES(models.TextChoices):
        ACTIVE = "active", _("active")
        NEW = "new", _("new")

    scan_levels = [scan_level.value for scan_level in SCAN_LEVEL]

    user = models.ForeignKey("account.KATUser", on_delete=models.PROTECT, related_name="members")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="members")
    groups = models.ManyToManyField(Group, blank=True)
    status = models.CharField(choices=STATUSES.choices, max_length=64, default=STATUSES.NEW)
    blocked = models.BooleanField(default=False)
    onboarded = models.BooleanField(default=False)
    trusted_clearance_level = models.IntegerField(
        default=-1, validators=[MinValueValidator(-1), MaxValueValidator(max(scan_levels))]
    )
    acknowledged_clearance_level = models.IntegerField(
        default=-1, validators=[MinValueValidator(-1), MaxValueValidator(max(scan_levels))]
    )

    @cached_property
    def all_permissions(self) -> Set[str]:
        if self.user.is_active and self.user.is_superuser:
            # Superuser always has all permissions
            return {
                f"{ct}.{name}" for ct, name in Permission.objects.values_list("content_type__app_label", "codename")
            }

        if self.blocked or not self.user.is_active:
            # A blocked or inactive user doesn't have any permissions specific to this organization
            organization_member_perms = set()
        else:
            organization_member_perms = {
                f"{ct}.{name}"
                for ct, name in Permission.objects.filter(group__organizationmember=self).values_list(
                    "content_type__app_label", "codename"
                )
            }
        return organization_member_perms | self.user.get_all_permissions()

    def has_perm(self, perm: str) -> bool:
        return perm in self.all_permissions

    def has_perms(self, perm_list: Iterable[str]) -> bool:
        return all(self.has_perm(perm) for perm in perm_list)

    class Meta:
        unique_together = ["user", "organization"]

    def __str__(self):
        return str(self.user)


class Indemnification(models.Model):
    user = models.ForeignKey("account.KATUser", on_delete=models.SET_NULL, null=True)
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
        super().save(*args, **kwargs)

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
        if not self.data["description"]:
            self.get_internet_description()
        return self.data["description"]

    def get_internet_description(self):
        for key, value in get_info(ooi_type=self.type, natural_key=self.value).items():
            self.data[key] = value
        self.save()

    def __str__(self):
        return self.id
