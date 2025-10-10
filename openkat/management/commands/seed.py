import logging

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.core.management import BaseCommand

from objects.models import Hostname, Network, object_type_by_name
from openkat.models import GROUP_ADMIN, GROUP_CLIENT, GROUP_REDTEAM
from plugins.models import BusinessRule
from plugins.plugins.business_rules import get_rules
from tasks.models import ObjectSet


class Command(BaseCommand):
    help = "Creates the development organization, member, groups and set permissions."

    def get_permissions(self, codenames):
        permission_objects = []
        if codenames:
            for codename in codenames:
                try:
                    permission = Permission.objects.get(codename=codename)
                except Permission.DoesNotExist:
                    raise ObjectDoesNotExist("Permission:" + codename + " does not exist.")
                else:
                    permission_objects.append(permission.pk)

        return permission_objects

    def setup_kat_groups(self):
        self.group_admin, self.group_admin_created = Group.objects.get_or_create(name=GROUP_ADMIN)
        self.group_redteam, self.group_redteam_created = Group.objects.get_or_create(name=GROUP_REDTEAM)
        self.group_client, self.group_client_created = Group.objects.get_or_create(name=GROUP_CLIENT)

    def handle(self, *args, **options):
        self.setup_kat_groups()
        self.setup_group_permissions()
        Network.objects.get_or_create(name="internet")
        ObjectSet.objects.get_or_create(
            name="mail_server",
            description="Mail servers are hostnames that have an MX record pointed to them.",
            dynamic=True,
            object_type=ContentType.objects.get_for_model(Hostname),
            object_query=Hostname.Q.mail_server,
        )
        ObjectSet.objects.get_or_create(
            name="name_server",
            description="Name servers are hostnames that have an NS record pointed to them.",
            dynamic=True,
            object_type=ContentType.objects.get_for_model(Hostname),
            object_query=Hostname.Q.name_server,
        )
        ObjectSet.objects.get_or_create(
            name="root_domains",
            description="Root domains are hostnames that represent the registered domain (e.g., example.com).",
            dynamic=True,
            object_type=ContentType.objects.get_for_model(Hostname),
            object_query=Hostname.Q.root_domain,
        )
        self.seed_business_rules()

    def seed_business_rules(self):
        for rule_data in get_rules().values():
            BusinessRule.objects.update_or_create(
                name=rule_data["name"],
                defaults={
                    "description": rule_data["description"],
                    "enabled": True,
                    "finding_type_code": rule_data["finding_type_code"],
                    "object_type": ContentType.objects.get_for_model(object_type_by_name()[rule_data["object_type"]]),
                    "query": rule_data["query"],
                },
            )

        logging.info("Business rules seeded successfully")

    def setup_group_permissions(self):
        redteamer_permissions = ["can_scan_organization", "can_set_clearance_level"]

        redteam_permissions = self.get_permissions(redteamer_permissions)
        self.group_redteam.permissions.set(redteam_permissions)

        admin_permissions = self.get_permissions(
            redteamer_permissions
            + [
                "view_organization",
                "view_organizationmember",
                "add_organizationmember",
                "change_organization",
                "can_scan_organization",
                "change_organizationmember",
                "add_indemnification",
            ]
        )
        self.group_admin.permissions.set(admin_permissions)

        client_permissions = self.get_permissions(["can_scan_organization"])
        self.group_client.permissions.set(client_permissions)

        logging.info("OPENKAT HAS BEEN SETUP SUCCESSFULLY")
