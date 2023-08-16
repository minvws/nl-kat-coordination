from datetime import datetime, timezone
from typing import List, Optional

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.utils.translation import gettext_lazy as _
from django.views import View
from requests import RequestException
from tools.enums import CUSTOM_SCAN_LEVEL
from tools.models import Organization, OrganizationMember

from octopoes.connector import RemoteException
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import DeclaredScanProfile, EmptyScanProfile, Reference, ScanLevel
from octopoes.models.exception import ObjectNotFoundException
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


class OOIClearanceMixin:
    def get_no_clearance_notifications(self, level=None):
        if not self.organization_member.indemnification_present:
            messages.add_message(
                self.request,
                messages.WARNING,
                _(
                    "Indemnification not present at organization {}. Go to the organization settings page to set this."
                ).format(self.organization.name),
            )

        if not self.organization_member.has_perm("tools.can_set_clearance_level"):
            messages.add_message(
                self.request, messages.ERROR, _("You don't have the required permission to set clearance levels.")
            )

        if self.organization_member.trusted_clearance_level < 0:
            messages.add_message(
                self.request,
                messages.WARNING,
                _(
                    "Your administrator has not assigned to you a trusted clearance level. "
                    "Contact your administrator to set a trusted clearance level to continue."
                ),
            )

        if not self.organization_member.is_trusted_clearance_level_acknowledged:
            messages.add_message(
                self.request,
                messages.WARNING,
                _(
                    "Your administrator has trusted you to set clearance levels on OOIs to a maximum level of {}, "
                    "however you did not acknowledge this clearance level yet. Go to your profile to set this."
                ).format(self.organization_member.trusted_clearance_level),
            )

    def get_success_notifications(self, level, counted_oois):
        extra_message = ""
        if counted_oois > 1:
            extra_message = f"for {counted_oois} OOIs"
        messages.add_message(
            self.request,
            messages.SUCCESS,
            _("Successfully changed clearance level to {} " + extra_message).format(level),
        )

    def change_clearance_level(self, ooi_references: List[Reference], level: int | str) -> None:
        if not ooi_references:
            messages.add_message(self.request, messages.ERROR, _("No OOIs selected to set clearance level."))
            return self.get(self.request, *self.args, **self.kwargs)
        try:
            if level == CUSTOM_SCAN_LEVEL.INHERIT.value:
                self.octopoes_api_connector.save_many_scan_profiles(
                    [EmptyScanProfile(reference=Reference.from_str(ooi)) for ooi in ooi_references],
                    valid_time=datetime.now(timezone.utc),
                )
                self.get_success_notifications(level, len(ooi_references))
            elif (
                isinstance(level, int)
                and self.organization_member.has_ooi_clearance
                and level <= self.organization_member.trusted_clearance_level
            ):
                self.octopoes_api_connector.save_many_scan_profiles(
                    [DeclaredScanProfile(reference=reference, level=ScanLevel(level)) for reference in ooi_references],
                    datetime.now(timezone.utc),
                )
                self.get_success_notifications(level, len(ooi_references))
            else:
                self.get_no_clearance_notifications(level)
                messages.add_message(
                    self.request,
                    messages.ERROR,
                    _(
                        "Could not change clearance level to level {}. You can change clearance level to a maximum of "
                        "level {}. Contact your administrator to receive a higher clearance."
                    ).format(level, self.organization_member.trusted_clearance_level),
                )

        except (RequestException, RemoteException, ConnectionError):
            messages.add_message(self.request, messages.ERROR, _("An error occurred while changing clearance levels."))

        except ObjectNotFoundException:
            messages.add_message(
                self.request,
                messages.ERROR,
                _("An error occurred while changing clearance levels. One of the OOI's doesn't exist"),
            )


class OrganizationView(View, OOIClearanceMixin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.organization: Optional[Organization] = None
        self.octopoes_api_connector: Optional[OctopoesAPIConnector] = None
        self.bytes_client: BytesClient = None
        self.organization_member = None

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


class OrganizationPermissionRequiredMixin(PermissionRequiredMixin):
    """
    This mixin will check the permission based on OrganizationMember instead of User.
    """

    def has_permission(self) -> bool:
        perms = self.get_permission_required()
        return self.organization_member.has_perms(perms)
