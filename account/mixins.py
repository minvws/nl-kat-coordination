from django.contrib import messages
from django.http import Http404
from django.utils.translation import gettext_lazy as _
from django.views import View

from octopoes.connector.octopoes import OctopoesAPIConnector
from rocky.settings import OCTOPOES_API
from tools.models import Organization, OrganizationMember, Indemnification


class OrganizationView(View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.organization = None
        self.octopoes_api_connector = None
        self._may_update_scan_profile = False
        self.organization_member = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        organization_code = kwargs["organization_code"]
        try:
            self.organization = Organization.objects.get(code=organization_code)
        except Organization.DoesNotExist:
            self.organization = None
        try:
            self.organization_member = OrganizationMember.objects.get(
                user=self.request.user, organization=self.organization
            )
        except OrganizationMember.DoesNotExist:
            self.organization_member = None

        self.octopoes_api_connector = OctopoesAPIConnector(OCTOPOES_API, organization_code)

    def dispatch(self, request, *args, **kwargs):

        if self.organization is None or self.organization_member is None:
            raise Http404()

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.organization:
            context["organization"] = self.organization
        context["organization_member"] = self.organization_member
        context["may_update_scan_profile"] = self.may_update_scan_profile
        return context

    @property
    def may_update_scan_profile(self):
        if not Indemnification.objects.filter(organization=self.organization).exists():
            return False
        if self.organization_member.acknowledged_clearance_level < 0:
            return False
        if self.organization_member.trusted_clearance_level < 0:
            return False
        return True

    def verify_may_update_scan_profile(self) -> bool:
        if not Indemnification.objects.filter(organization=self.organization).exists():
            messages.add_message(self.request, messages.ERROR, _("No indemnification present for organization."))
            return False

        if self.organization_member.acknowledged_clearance_level < 0:
            messages.add_message(self.request, messages.ERROR, _("Acknowledged clearance level too low."))
            return False

        if self.organization_member.trusted_clearance_level < 0:
            messages.add_message(self.request, messages.ERROR, _("Trusted clearance level too low."))
            return False
        return True
