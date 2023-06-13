import logging

from django.conf import settings
from django.contrib.auth.backends import RemoteUserBackend as BaseRemoteUserBackend
from django.contrib.auth.models import Group
from tools.models import Organization, OrganizationMember

logger = logging.getLogger(__name__)


class RemoteUserBackend(BaseRemoteUserBackend):
    """
    Custom RemoteUserBackend that adds users to default organizations and groups.
    """

    def configure_user(self, request, user, created=True):
        if settings.REMOTE_USER_DEFAULT_ORGANIZATIONS:
            try:
                user_orgs = [o.code for o in user.organizations]
                for item in settings.REMOTE_USER_DEFAULT_ORGANIZATIONS:
                    organization_name, group_name = item.split(":")
                    if organization_name not in user_orgs:
                        logger.info("Adding user '%s' to organization '%s'", user, organization_name)
                        organization = Organization.objects.get(code=organization_name)
                        member = OrganizationMember.objects.create(
                            user=user,
                            organization=organization,
                            status=OrganizationMember.STATUSES.ACTIVE,
                            blocked=False,
                            trusted_clearance_level=4,
                            acknowledged_clearance_level=0,
                            onboarded=False,
                        )
                        member.groups.set([Group.objects.get(name=group_name)])
                        del user.organizations
            except Exception:
                logger.exception("An error occurred while configuring user '%s'", user)
        return user
