from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from django.core.management import BaseCommand
from django.contrib.auth.models import Permission
from django.core.exceptions import ObjectDoesNotExist
from tools.models import GROUP_CLIENT, GROUP_REDTEAM, GROUP_ADMIN

User = get_user_model()


class Command(BaseCommand):
    help = "Creates initial user and groups"

    def add_arguments(self, parser):
        parser.add_argument(
            "--username", action="store", type=str, help="Superuser username"
        )
        parser.add_argument("--email", action="store", type=str, help="Superuser email")
        parser.add_argument(
            "--password", action="store", type=str, help="Superuser password"
        )

    def get_permissions(self, codenames):
        permission_objects = []
        permission = None
        if codenames:
            for codename in codenames:
                try:
                    permission = Permission.objects.get(codename=codename)
                    permission_objects.append(permission.id)
                except:
                    raise ObjectDoesNotExist(
                        "Permission:" + str(permission) + " does not exist."
                    )
        return permission_objects

    def create_kat_superuser(self, options):
        superuser, superuser_created = User.objects.get_or_create(
            username=options["username"]
        )
        if superuser_created:
            superuser.set_password(options["password"])
            superuser.is_staff = True
            superuser.is_superuser = True
            superuser.save()

    def setup_kat_groups(self):
        self.group_admin, self.group_admin_created = Group.objects.get_or_create(
            name=GROUP_ADMIN
        )

        self.group_redteam, self.group_redteam_created = Group.objects.get_or_create(
            name=GROUP_REDTEAM
        )

        Group.objects.get_or_create(name=GROUP_CLIENT)

    def handle(self, **options):
        self.create_kat_superuser(options)
        self.setup_kat_groups()

        admin_permissions = self.get_permissions(
            [
                "view_organizationmember",
                "add_organizationmember",
            ]
        )
        self.group_admin.permissions.set(admin_permissions)

        redteam_permissions = self.get_permissions(
            [
                "can_switch_organization",
                "can_scan_organization",
                "can_enable_disable_boefje",
            ]
        )
        self.group_redteam.permissions.set(redteam_permissions)
