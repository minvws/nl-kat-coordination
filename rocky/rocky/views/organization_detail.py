from django.contrib import messages
from account.mixins import OrganizationView
from django.utils.translation import gettext_lazy as _
from django_otp.decorators import otp_required
from two_factor.views.utils import class_view_decorator

from rocky.views.organization_member_list import OrganizationMemberListView


@class_view_decorator(otp_required)
class OrganizationDetailView(OrganizationMemberListView, OrganizationView):
    template_name = "organizations/organization_detail.html"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        if not self.indemnification_present:
            messages.add_message(self.request, messages.ERROR, _("Indemnification is not set for this organization."))
