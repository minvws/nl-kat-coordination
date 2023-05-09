from datetime import datetime, timezone
from typing import List

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
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


class OrganizationSetupView(View):
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.organization_code = kwargs.get("organization_code", None)
        self.organization = get_object_or_404(Organization, code=self.organization_code)
        self.organization_member = get_object_or_404(
            OrganizationMember, user=self.request.user, organization=self.organization
        )
        if self.organization_member.blocked:
            raise PermissionDenied()
        self.octopoes_api_connector = OctopoesAPIConnector(settings.OCTOPOES_API, self.organization_code)


class OrganizationView(OrganizationSetupView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.organization = None
        self.octopoes_api_connector = None
        self.organization_member = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["organization"] = self.organization
        context["organization_member"] = self.organization_member
        return context


class ClearanceRequiredView(OrganizationSetupView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.indemnification_present = False

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.indemnification_present = Indemnification.objects.filter(organization=self.organization).exists()

    @property
    def may_update_clearance_level(self) -> bool:
        if not self.indemnification_present:
            return False
        if self.organization_member.acknowledged_clearance_level < 0:
            return False
        if self.organization_member.trusted_clearance_level < 0:
            return False
        return True

    def verify_clearance_start_scan(self, clearance_levels: List[int]) -> bool:
        return any(
            [
                clearance_level <= self.organization_member.acknowledged_clearance_level
                for clearance_level in clearance_levels
            ]
        )

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["may_update_clearance_level"] = self.may_update_clearance_level
        context["indemnification_present"] = self.indemnification_present
        return context
