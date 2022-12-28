from colorama import Fore
import logging
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from django.core.management import BaseCommand
from django.contrib.auth.models import Permission
from django.core.exceptions import ObjectDoesNotExist

from tools.models import (
    SCAN_LEVEL,
    Organization,
    OrganizationMember,
    GROUP_CLIENT,
    GROUP_REDTEAM,
    GROUP_ADMIN,
)

User = get_user_model()


class Command(BaseCommand):
    help = "Creates the development organization, member, groups and set permissions."

    def setup_dev_organization_and_member(self):

        dev_org, _ = Organization.objects.get_or_create(name="Development Organization", code="_dev")

        dev_user = User.objects.last()

        scan_levels = [scan_level.value for scan_level in SCAN_LEVEL]

        OrganizationMember.objects.create(
            user=dev_user,
            organization=dev_org,
            verified=True,
            authorized=True,
            status=OrganizationMember.STATUSES.ACTIVE,
            trusted_clearance_level=max(scan_levels),
            acknowledged_clearance_level=max(scan_levels),
        )

    def get_permissions(self, codenames):
        permission_objects = []
        permission = None
        if codenames:
            for codename in codenames:
                try:
                    permission = Permission.objects.get(codename=codename)
                    permission_objects.append(permission.id)
                except permission.DoesNotExist:
                    raise ObjectDoesNotExist("Permission:" + str(permission) + " does not exist.")
        return permission_objects

    def setup_kat_groups(self):
        self.group_admin, self.group_admin_created = Group.objects.get_or_create(name=GROUP_ADMIN)

        self.group_redteam, self.group_redteam_created = Group.objects.get_or_create(name=GROUP_REDTEAM)

        Group.objects.get_or_create(name=GROUP_CLIENT)

    def handle(self, *args, **options):
        self.setup_dev_organization_and_member()
        self.setup_kat_groups()

        admin_permissions = self.get_permissions(
            [
                "view_organization",
                "view_organizationmember",
                "add_organizationmember",
            ]
        )
        self.group_admin.permissions.set(admin_permissions)

        redteam_permissions = self.get_permissions(
            [
                "can_scan_organization",
                "can_enable_disable_boefje",
                "can_set_clearance_level",
            ]
        )
        self.group_redteam.permissions.set(redteam_permissions)
        logging.info(Fore.GREEN + " ROCKY HAS BEEN SETUP SUCCESSFULLY")
