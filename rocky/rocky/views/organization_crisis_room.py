from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django_otp.decorators import otp_required
from two_factor.views.utils import class_view_decorator
from rocky.views.finding_list import Top10FindingListView


@class_view_decorator(otp_required)
class OrganizationCrisisRoomView(Top10FindingListView):
    template_name = "organizations/organization_crisis_room.html"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        if not self.indemnification_present:
            messages.add_message(self.request, messages.ERROR, _("Indemnification is not set for this organization."))
