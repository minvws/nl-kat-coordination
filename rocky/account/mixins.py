from datetime import datetime, timezone
from typing import List, Optional

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.utils.translation import gettext_lazy as _
from django.views import View
from tools.models import Organization, OrganizationMember

from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import DeclaredScanProfile, Reference, ScanLevel
from rocky.bytes_client import BytesClient, get_bytes_client


# There are modified versions of PermLookupDict and PermWrapper from
# django.contrib.auth.context_processor.
class OrganizationPermLookupDict:
    def __init__(self, organization_member, app_label):
        self.organization_member, self.app_label = organization_member, app_label

    def __repr__(self):
        return str(self.organization_member.get_all_permissions)

    def __getitem__(self, perm_name):
        return self.organization_member.has_perm(f"{self.app_label}.{perm_name}")

    def __iter__(self):
        # To fix 'item in perms.someapp' and __getitem__ interaction we need to
        # define __iter__. See #18979 for details.
        raise TypeError("PermLookupDict is not iterable.")

    def __bool__(self):
        return False


class OrganizationPermWrapper:
    def __init__(self, organization_member):
        self.organization_member = organization_member

    def __repr__(self):
        return f"{self.__class__.__qualname__}({self.organization_member!r})"

    def __getitem__(self, app_label):
        return OrganizationPermLookupDict(self.organization_member, app_label)

    def __iter__(self):
        # I am large, I contain multitudes.
        raise TypeError("PermWrapper is not iterable.")

    def __contains__(self, perm_name):
        """
        Lookup by "someapp" or "someapp.someperm" in perms.
        """
        if "." not in perm_name:
            # The name refers to module.
            return bool(self[perm_name])
        app_label, perm_name = perm_name.split(".", 1)
        return self[app_label][perm_name]


class OrganizationView(View):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.organization: Optional[Organization] = None
        self.octopoes_api_connector: Optional[OctopoesAPIConnector] = None
        self.bytes_client: BytesClient = None
        self.organization_member = None
        self.clearance_errors = {}

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)

        organization_code = kwargs["organization_code"]
        try:
            self.organization = Organization.objects.get(code=organization_code)
        except Organization.DoesNotExist:
            raise Http404()

        try:
            self.organization_member = OrganizationMember.objects.get(
                user=self.request.user, organization=self.organization
            )
        except OrganizationMember.DoesNotExist:
            raise Http404()

        if self.organization_member.blocked:
            raise PermissionDenied()

        self.octopoes_api_connector = OctopoesAPIConnector(settings.OCTOPOES_API, organization_code)
        self.bytes_client = get_bytes_client(organization_code)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["organization"] = self.organization
        context["organization_member"] = self.organization_member
        context["perms"] = OrganizationPermWrapper(self.organization_member)
        return context

    def can_raise_clearance_level(self, level: int) -> bool:
        if (
            self.organization_member.has_ooi_clearance
            and level <= self.organization_member.acknowledged_clearance_level
        ):
            return True
        self.clearance_errors["raise_clearance_level"] = _(
            "Could not raise clearance level to L{}. You can raise clearance level to a maximum of L{}."
        ).format(level, self.organization_member.acknowledged_clearance_level)

        if not self.organization_member.indemnification_present:
            self.clearance_errors["indemnification_present"] = _(
                "Indemnification not present at organization {}."
            ).format(self.organization.name)

        return False

    def raise_clearance_level(self, ooi_reference: Reference, level: int) -> bool:
        if self.can_raise_clearance_level(level):
            self.octopoes_api_connector.save_scan_profile(
                DeclaredScanProfile(reference=ooi_reference, level=ScanLevel(level)),
                datetime.now(timezone.utc),
            )
        else:
            self.error_message_no_clearance()

    def raise_clearance_levels(self, ooi_references: List[Reference], level: int) -> bool:
        if self.can_raise_clearance_level(level):
            self.octopoes_api_connector.save_many_scan_profiles(
                [DeclaredScanProfile(reference=reference, level=ScanLevel(level)) for reference in ooi_references],
                datetime.now(timezone.utc),
            )
        else:
            self.error_message_no_clearance()

    def error_message_no_clearance(self):
        clearance_messages = ""
        for error in self.clearance_errors.values():
            clearance_messages += error

        messages.add_message(self.request, messages.ERROR, clearance_messages)


class OrganizationPermissionRequiredMixin(PermissionRequiredMixin):
    """
    This mixin will check the permission based on OrganizationMember instead of User.
    """

    def has_permission(self) -> bool:
        perms = self.get_permission_required()
        return self.organization_member.has_perms(perms)
