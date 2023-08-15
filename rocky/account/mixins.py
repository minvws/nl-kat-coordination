from datetime import datetime, timezone
from typing import List, Optional

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpRequest, HttpResponse
from django.utils.translation import gettext_lazy as _
from django.views import View
from requests import RequestException
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
    def get_clearance_notifications(self):
        if not self.organization_member.indemnification_present:
            messages.add_message(
                self.request,
                messages.ERROR,
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
                messages.ERROR,
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
                    "Your administrator has trusted you to set clearance levels on OOIs to a maximum of L{}, "
                    "however you did not acknowledge this clearance level yet. Go to your profile to set this."
                ).format(self.organization_member.trusted_clearance_level),
            )

    def can_raise_clearance_level(self, level: int) -> bool:
        if not self.organization_member.has_ooi_clearance:
            self.get_clearance_notifications()
            return False
        if level > self.organization_member.trusted_clearance_level:
            messages.add_message(
                self.request,
                messages.ERROR,
                _(
                    "Could not raise clearance level to L{}. You can raise clearance level to a maximum of L{}. "
                    "Contact your administrator to receive a higher clearance."
                ).format(level, self.organization_member.trusted_clearance_level),
            )
            return False
        return True

    def raise_clearance_level(self, ooi_references: Reference | List[Reference], level: int) -> HttpResponse:
        try:
            if self.can_raise_clearance_level(level):
                if isinstance(ooi_references, list):
                    self.octopoes_api_connector.save_many_scan_profiles(
                        [
                            DeclaredScanProfile(reference=reference, level=ScanLevel(level))
                            for reference in ooi_references
                        ],
                        datetime.now(timezone.utc),
                    )
                else:
                    self.octopoes_api_connector.save_scan_profile(
                        DeclaredScanProfile(reference=ooi_references, level=ScanLevel(level)),
                        datetime.now(timezone.utc),
                    )
                messages.add_message(
                    self.request,
                    messages.SUCCESS,
                    _("Successfully raised clearance level to L{}.").format(level),
                )

        except (RequestException, RemoteException, ConnectionError):
            messages.add_message(self.request, messages.ERROR, _("An error occurred while saving clearance levels."))

        except ObjectNotFoundException:
            messages.add_message(
                self.request,
                messages.ERROR,
                _("An error occurred while saving clearance levels.") + _("One of the OOI's doesn't exist"),
            )
        return self.get(self.request, *self.args, **self.kwargs)

    def _set_oois_to_inherit(
        self, selected_oois: List[Reference], request: HttpRequest, *args, **kwargs
    ) -> HttpResponse:
        scan_profiles = [EmptyScanProfile(reference=Reference.from_str(ooi)) for ooi in selected_oois]

        try:
            self.octopoes_api_connector.save_many_scan_profiles(scan_profiles, valid_time=datetime.now(timezone.utc))
        except (RequestException, RemoteException, ConnectionError):
            messages.add_message(
                request,
                messages.ERROR,
                _("An error occurred while setting clearance levels to inherit."),
            )
        except ObjectNotFoundException:
            messages.add_message(
                request,
                messages.ERROR,
                _("An error occurred while setting clearance levels to inherit: one of the OOIs doesn't exist."),
            )

        messages.add_message(
            request,
            messages.SUCCESS,
            _("Successfully set %d ooi(s) clearance level to inherit.") % len(selected_oois),
        )
        return self.get(request, *args, **kwargs)


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
