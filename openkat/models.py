from datetime import datetime
from typing import Any, ClassVar

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager["User"]):
    """
    Kat user model manager.

    Email is the unique identifiers for authentication instead of usernames.
    """

    def create_user(self, email: str, password: str | None, **extra_fields: Any) -> "User":
        """Create and save a User with the given email and password."""
        if not email:
            raise ValueError(_("The Email must be set"))
        user: User = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email: str, password: str | None, **extra_fields: Any) -> "User":
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))
        return self.create_user(email, password, **extra_fields)


class LowerCaseCharField(models.CharField[str, str]):
    """Override CharField to convert value to lowercase before saving."""

    def to_python(self, value: Any | None) -> str | None:
        """Convert email to lowercase."""
        str_value: str = super().to_python(value)
        if str_value is None:
            return None

        return str_value.lower()

    def pre_save(self, model_instance: models.Model, add: bool) -> str | None:  # noqa: FBT001, ARG002
        value: str | None = getattr(model_instance, self.attname)
        if value:
            value = value.lower()
            setattr(model_instance, self.attname, value)
        return value


class LowerCaseEmailField(LowerCaseCharField, models.EmailField[str, str]):
    """Override EmailField to convert emails to lowercase before saving."""


class User(AbstractBaseUser, PermissionsMixin):
    id: int
    full_name: models.CharField[str, str] = models.CharField(_("full name"), max_length=150)
    email: LowerCaseEmailField = LowerCaseEmailField(_("email"), max_length=254, unique=True)
    is_staff: models.BooleanField[bool, bool] = models.BooleanField(
        _("staff status"), default=False, help_text=_("Designates whether the user can log into this admin site.")
    )
    is_active: models.BooleanField[bool, bool] = models.BooleanField(
        _("active"),
        default=True,
        help_text=_(
            "Designates whether this user should be treated as active. Unselect this instead of deleting accounts."
        ),
    )
    date_joined: models.DateTimeField[datetime, datetime] = models.DateTimeField(_("date joined"), default=timezone.now)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: ClassVar[list[str]] = ["full_name"]

    objects = UserManager()

    class Meta:
        managed = False


class Organization(models.Model):
    id: int
    name: models.CharField[str, str] = models.CharField(
        max_length=126, unique=True, help_text=_("The name of the organisation")
    )

    class Meta:
        managed = False

    def __str__(self) -> str:
        return self.name
