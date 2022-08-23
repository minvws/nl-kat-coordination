import uuid
from typing import Optional

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from requests.exceptions import HTTPError

from tools.add_ooi_information import get_info, SEPARATOR
from tools.validators import phone_validator

User = get_user_model()

GROUP_ADMIN = "admin"
GROUP_REDTEAM = "redteam"
GROUP_CLIENT = "clients"


class SCAN_LEVEL(models.IntegerChoices):
    L0 = 0, "L0"
    L1 = 1, "L1"
    L2 = 2, "L2"
    L3 = 3, "L3"
    L4 = 4, "L4"


class Organization(models.Model):
    name = models.CharField(max_length=126, unique=True)
    code = models.CharField(max_length=8, unique=True, default=None, null=True)
    signal_username = models.CharField(
        validators=[phone_validator], max_length=126, unique=True, blank=True, null=True
    )
    signal_group_id = models.CharField(max_length=126, blank=True, null=True)

    def __str__(self):
        return str(self.name)

    def has_signal_group(self):
        if self.signal_username is None or self.signal_group_id is None:
            return False

        return True

    class Meta:
        permissions = (
            ("can_switch_organization", "Can switch organization"),
            ("can_scan_organization", "Can scan organization"),
            ("can_enable_disable_boefje", "Can enable or disable boefje"),
        )

    def get_absolute_url(self):
        return reverse("organization_detail", args=[self.pk])


class OrganizationMember(models.Model):
    class STATUSES(models.TextChoices):
        ACTIVE = "active", _("active")
        NEW = "new", _("new")
        BLOCKED = "blocked", _("blocked")

    user = models.OneToOneField(User, on_delete=models.DO_NOTHING)
    organization = models.ForeignKey(
        Organization, on_delete=models.SET_NULL, null=True, related_name="members"
    )
    verified = models.BooleanField(default=False)
    authorized = models.BooleanField(default=False)
    status = models.CharField(
        choices=STATUSES.choices, max_length=64, default=STATUSES.NEW
    )
    member_name = models.CharField(max_length=126)
    member_role = models.CharField(max_length=126)
    goal = models.CharField(max_length=256)
    signal_username = models.CharField(
        validators=[phone_validator],
        max_length=126,
        unique=True,
        default=None,
        blank=True,
        null=True,
    )
    onboarded = models.BooleanField(default=False)

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
    def description(self) -> Optional[str]:
        if self.data["description"] == "":
            try:
                self.get_internet_description()
            except HTTPError:
                return None
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
