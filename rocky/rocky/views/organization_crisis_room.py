from django_otp.decorators import otp_required
from two_factor.views.utils import class_view_decorator
from rocky.views.finding_list import Top10FindingListView


@class_view_decorator(otp_required)
class OrganizationCrisisRoomView(Top10FindingListView):
    template_name = "organizations/organization_crisis_room.html"
