from datetime import datetime, timezone

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.contrib.auth.mixins import PermissionRequiredMixin
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

        # authentication/otp flow happens before setup
        if not request.user.is_authenticated:
            return

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


class RockyPermissionRequiredMixin(PermissionRequiredMixin):
    """
    An organization member can have different roles and set of permssions based on which organization they belong to.
    We do not want to check permissions based soley on the user but instead on the organization member.
    """

    def has_permission(self) -> bool:
        user_perm = super().has_permission()
        if user_perm:
            return user_perm
        try:
            organization_code = self.kwargs["organization_code"]
            organization = Organization.objects.get(code=organization_code)
            member = OrganizationMember.objects.get(user=self.request.user, organization=organization)
        except OrganizationMember.DoesNotExist:
            raise Http404()
        return member.has_member_perm(self.permission_required)
