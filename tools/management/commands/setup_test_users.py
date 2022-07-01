from typing import Optional, Dict

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import BaseCommand
from django_otp.plugins.otp_totp.models import TOTPDevice

from tools.models import (
    GROUP_CLIENT,
    GROUP_REDTEAM,
    GROUP_ADMIN,
    Organization,
    OrganizationMember,
)

User = get_user_model()


class Command(BaseCommand):
    help = "Creates test users and groups"

    def handle(self, **options):
        password = "Test123!"
        add_superuser("e2e-superuser", password)
        add_test_user("e2e-admin", password, GROUP_ADMIN)
        add_test_user("e2e-redteam", password, GROUP_REDTEAM)
        add_test_user("e2e-client", password, GROUP_CLIENT)


def add_superuser(username: str, password: str):
    user_kwargs = {
        "username": username,
        "password": password,
        "first_name": "End-to-end Superuser",
        "last_name": username,
        "email": "{}@openkat.nl".format(username),
        "is_staff": True,
        "is_superuser": True,
    }

    add_user(user_kwargs)


def add_test_user(username: str, password: str, group_name: Optional[str] = None):
    user_kwargs = {
        "username": username,
        "password": password,
        "first_name": "End-to-end user",
        "last_name": username,
        "email": "{}@openkat.nl".format(username),
    }

    add_user(user_kwargs, group_name)


def add_user(user_kwargs: Dict[str, str], group_name: Optional[str] = None):
    """
    Creates a test user with the given user_kwargs.
    User is optionally added to group group_name.
    """
    if group_name and group_name not in [GROUP_CLIENT, GROUP_REDTEAM, GROUP_ADMIN]:
        raise ValueError("Invalid group name")

    # get or create user
    if User.objects.filter(username=user_kwargs["username"]).exists():
        user = User.objects.get(username=user_kwargs["username"])
    else:
        user = User.objects.create_user(**user_kwargs)

    # add to group if group_name provided
    if group_name:
        group = Group.objects.get(name=group_name)
        if not group.user_set.filter(username=user_kwargs["username"]).exists():
            group.user_set.add(user)

    # Setting OTP key for consistent secret
    TOTPDevice.objects.get_or_create(
        user=user,
        name="default",
        confirmed=True,
        key="980152be03d8b6d5c6598047b127f9a5469b8e5d",
        step=30,
        t0=0,
        digits=6,
        tolerance=1,
        drift=0,
        last_t=-1,
        throttling_failure_count=0,
        throttling_failure_timestamp=None,
    )

    organization, created = Organization.objects.get_or_create(code="_dev")

    organization_member, created = OrganizationMember.objects.get_or_create(
        user=user,
        organization=organization,
    )

    if created:
        organization_member.verified = True
        organization_member.authorized = True
        organization_member.status = OrganizationMember.STATUSES.ACTIVE
        organization_member.save()
