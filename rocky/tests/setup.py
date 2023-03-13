from unittest.mock import patch
import binascii
from os import urandom
from tools.models import Organization, OrganizationMember, Indemnification
from django.contrib.auth.models import Permission, Group
from tools.models import GROUP_REDTEAM, GROUP_ADMIN, GROUP_CLIENT


class OrganizationSetup:
    def __init__(
        self,
        organization_name="Test Organization",
        code="test",
        katalogus_client="katalogus.client.KATalogusClientV1",
        octopoes_node="octopoes.connector.octopoes.OctopoesAPIConnector.create_node",
    ):
        self.organization_name = organization_name
        self.organization_code = code
        self.katalogus_client = katalogus_client
        self.octopoes_node = octopoes_node

    def create_organization(self):
        with patch(self.katalogus_client), patch(self.octopoes_node):
            return Organization.objects.create(name=self.organization_name, code=self.organization_code)


class UserSetup:
    def __init__(
        self,
        user_model,
        email,
        password,
        full_name="OpenKat user",
        is_verified=lambda: True,
        device_name="default",
        device_token=binascii.hexlify(urandom(8)).decode(),
    ):
        self.user_model = user_model
        self.email = email
        self.password = password
        self.full_name = full_name
        self.is_verified = is_verified
        self.device_name = device_name
        self.device_token = device_token

    def setup_device(self, user):
        device = user.staticdevice_set.create(name=self.device_name)
        device.token_set.create(token=self.device_token)

    def _create_admin_user(self):
        admin_user = self.user_model.objects.create_user(email=self.email, password=self.password)
        admin_user.full_name = self.full_name
        admin_user.is_verified = self.is_verified
        admin_user.save()
        self.setup_device(admin_user)
        group, _ = Group.objects.get_or_create(name=GROUP_ADMIN)
        group.user_set.add(admin_user)

        admin_permissions = [
            Permission.objects.get(codename="view_organization").id,
            Permission.objects.get(codename="view_organizationmember").id,
            Permission.objects.get(codename="add_organizationmember").id,
            Permission.objects.get(codename="change_organizationmember").id,
            Permission.objects.get(codename="change_organization").id,
        ]
        group.permissions.set(admin_permissions)
        return admin_user

    def _create_redteam_user(self):
        redteam_user = self.user_model.objects.create_user(email=self.email, password=self.password)
        redteam_user.full_name = self.full_name
        redteam_user.is_verified = self.is_verified
        redteam_user.save()
        self.setup_device(redteam_user)
        group, _ = Group.objects.get_or_create(name=GROUP_REDTEAM)
        group.user_set.add(redteam_user)

        redteam_permissions = [
            Permission.objects.get(codename="can_scan_organization").id,
            Permission.objects.get(codename="can_enable_disable_boefje").id,
            Permission.objects.get(codename="can_set_clearance_level").id,
        ]
        group.permissions.set(redteam_permissions)
        return redteam_user

    def _create_client_user(self):
        client_user = self.user_model.objects.create_user(email=self.email, password=self.password)
        client_user.full_name = self.full_name
        client_user.is_verified = self.is_verified
        client_user.save()
        self.setup_device(client_user)
        group, _ = Group.objects.get_or_create(name=GROUP_CLIENT)
        group.user_set.add(client_user)
        return client_user

    def _create_superuser(self):
        _superuser = self.user_model.objects.create_superuser(email=self.email, password=self.password)
        _superuser.full_name = self.full_name
        _superuser.is_verified = self.is_verified
        _superuser.save()
        self.setup_device(_superuser)
        return _superuser


class MemberSetup:
    def __init__(
        self,
        user,
        organization,
        member_status=OrganizationMember.STATUSES.ACTIVE,
        trusted_clearance_level=-1,
        acknowledged_clearance_level=-1,
        onboarded=False,
    ):
        self.user = user
        self.organization = organization
        self.member_status = member_status
        self.trusted_clearance_level = trusted_clearance_level
        self.acknowledged_clearance_level = acknowledged_clearance_level
        self.onboarded = onboarded

    def create_member(self):
        self.set_indemnification()
        return OrganizationMember.objects.create(
            user=self.user,
            organization=self.organization,
            status=self.member_status,
            trusted_clearance_level=self.trusted_clearance_level,
            acknowledged_clearance_level=self.acknowledged_clearance_level,
        )

    def set_indemnification(self):
        Indemnification.objects.create(
            organization=self.organization,
            user=self.user,
        )
