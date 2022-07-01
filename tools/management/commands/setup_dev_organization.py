from django.contrib.auth import get_user_model
from django.core.management import BaseCommand
from tools.models import Organization, OrganizationMember
from colorama import Fore
import logging

User = get_user_model()


class Command(BaseCommand):
    help = "Creates an organization for development purposes, with the supplied user as member"

    def add_arguments(self, parser):
        parser.add_argument(
            "--username", action="store", type=str, help="Superuser username"
        )

    def handle(self, **options):

        dev_org, created = Organization.objects.get_or_create(code="_dev")

        if dev_org.name == "":
            dev_org.name = "Development Organization"
        dev_org.save()

        admin, created = User.objects.get_or_create(
            username=options["username"],
        )

        org_member, created = OrganizationMember.objects.get_or_create(
            user=admin,
            organization=dev_org,
        )
        org_member.verified = True
        org_member.authorized = True
        org_member.status = OrganizationMember.STATUSES.ACTIVE
        logging.info(Fore.GREEN + " ROCKY HAS BEEN BUILT SUCCESSFULLY")
