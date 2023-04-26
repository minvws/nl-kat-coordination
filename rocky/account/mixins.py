from datetime import datetime, timezone
from typing import List, Union
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.utils.translation import gettext_lazy as _
from django.views import View
from tools.models import Indemnification, Organization, OrganizationMember

from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import DeclaredScanProfile, Reference, ScanLevel
from rocky.exceptions import (
    AcknowledgedClearanceLevelTooLowException,
    ClearanceLevelTooLowException,
    IndemnificationNotPresentException,
    TrustedClearanceLevelTooLowException,
)


class OrganizationView(View):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.organization = None
        self.octopoes_api_connector = None
        self.organization_member = None
        self.indemnification_present = False

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)

        organization_code = kwargs["organization_code"]
        try:
            self.organization = Organization.objects.get(code=organization_code)
        except Organization.DoesNotExist:
            raise Http404()

        self.indemnification_present = Indemnification.objects.filter(organization=self.organization).exists()

        try:
            self.organization_member = OrganizationMember.objects.get(
                user=self.request.user, organization=self.organization
            )
        except OrganizationMember.DoesNotExist:
            raise Http404()

        if self.organization_member.status == OrganizationMember.STATUSES.BLOCKED:
            raise PermissionDenied()

        self.octopoes_api_connector = OctopoesAPIConnector(settings.OCTOPOES_API, organization_code)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["organization"] = self.organization
        context["organization_member"] = self.organization_member
        context["may_update_clearance_level"] = self.may_update_clearance_level
        context["indemnification_present"] = self.indemnification_present
        return context

    @property
    def may_update_clearance_level(self) -> bool:
        if not self.indemnification_present:
            return False
        if self.organization_member.acknowledged_clearance_level < 0:
            return False
        if self.organization_member.trusted_clearance_level < 0:
            return False
        return True

    def verify_raise_clearance_level(self, level: int) -> bool:
        if not self.indemnification_present:
            raise IndemnificationNotPresentException()
        if self.organization_member.acknowledged_clearance_level < level:
            raise AcknowledgedClearanceLevelTooLowException()
        if self.organization_member.trusted_clearance_level < level:
            raise TrustedClearanceLevelTooLowException()
        return True

    def raise_clearance_level(self, ooi_reference: Reference, level: int) -> bool:
        try:
            self.verify_raise_clearance_level(level)
            self.octopoes_api_connector.save_scan_profile(
                DeclaredScanProfile(reference=ooi_reference, level=ScanLevel(level)),
                datetime.now(timezone.utc),
            )
        except IndemnificationNotPresentException as exc:
            messages.add_message(
                self.request,
                messages.ERROR,
                _(
                    "Could not raise clearance level of %s to L%s. \
                    Indemnification not present at organization %s."
                )
                % (
                    ooi_reference.human_readable,
                    level,
                    self.organization.name,
                ),
            )
            raise exc
        except ClearanceLevelTooLowException as exc:
            messages.add_message(
                self.request,
                messages.ERROR,
                _(
                    "Could not raise clearance level of %s to L%s. \
                    You acknowledged a clearance level of %s."
                )
                % (
                    ooi_reference.human_readable,
                    level,
                    self.organization_member.acknowledged_clearance_level,
                ),
            )
            raise exc
        return True


class MemberPermissionMixin:
    def get_member_permissions(self, member: OrganizationMember) -> List[str]:
        return [
            "%s.%s" % (ct, name)
            for ct, name in Permission.objects.filter(group__organizationmember=member).values_list(
                "content_type__app_label", "codename"
            )
        ]

    def has_member_perms(self, permission: Union[str, tuple], member) -> bool:
        if isinstance(permission, str):
            perms = (permission,)
        else:
            perms = permission
        member_permssions = self.get_member_permissions(member)
        for perm in perms:
            if perm in member_permssions:
                return True
        return False


class RockyPermissionRequiredMixin(PermissionRequiredMixin, MemberPermissionMixin):
    """
    An organization member can have different roles and set of permissions based on which organization they belong to.
    We do not want to check permissions based solely on the user but also on the organization member.
    """

    def has_permission(self) -> bool:
        user_perm = super().has_permission()
        if user_perm:
            return user_perm
        return self.has_member_perms(self.permission_required, self.organization_member)
