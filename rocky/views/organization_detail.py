from django_otp.decorators import otp_required
from two_factor.views.utils import class_view_decorator

from rocky.views.organization_member_list import OrganizationMemberListView


@class_view_decorator(otp_required)
class OrganizationDetailView(OrganizationMemberListView):
    template_name = "organizations/organization_detail.html"
