from logging import getLogger

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import BaseCommand, call_command
from django_otp.plugins.otp_totp.models import TOTPDevice

from tools.models import OrganizationMember, Indemnification

User = get_user_model()
logger = getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Helper command for testing and development purposes only: "
        "flushes the db but adds the first User, Organization and OrganizationMember again (including OTP setup)"
    )

    def handle(self, **options):
        if not User.objects.filter(id=1).exists():
            logger.info("No first user present")
            return

        device, first_user, groups, member, indemnification = self.collect_entities()

        call_command("flush", interactive=False)
        call_command("loaddata", "OOI_database_seed.json")
        call_command("setup_dev_account")

        self.save_entities_again(device, first_user, groups, member, indemnification)

    def collect_entities(self):
        first_user = User.objects.get(id=1)
        groups = Group.objects.filter(user=first_user)

        member, device, indemnification = None, None, None

        if OrganizationMember.objects.filter(user=first_user).exists():
            member = OrganizationMember.objects.filter(user=first_user).first()

            if Indemnification.objects.filter(user=first_user, organization=member.organization).exists():
                indemnification = Indemnification.objects.filter(
                    user=first_user, organization=member.organization
                ).first()

        if TOTPDevice.objects.filter(user=first_user).exists():
            device = TOTPDevice.objects.filter(user=first_user).first()

        if Indemnification.objects.filter(user=first_user).exists():
            device = TOTPDevice.objects.filter(user=first_user).first()

        return device, first_user, groups, member, indemnification

    def save_entities_again(self, device, first_user, groups, member, indemnification):
        first_user.save()
        logger.info("Saved user")

        for group in groups:
            group.user_set.add(first_user)
            logger.info("Added user to group %s", group.name)

        if device:
            device.save()
            logger.info("Saved device")

        if member:
            member.organization.save()
            logger.info("Saved organization %s again", member.organization.name)

            member.save()
            logger.info("Saved organization member again")

            if indemnification:
                indemnification.save()
                logger.info("Saved indemnification again")
