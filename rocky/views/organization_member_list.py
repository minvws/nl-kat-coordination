from typing import List

from django.views.generic import DetailView
from django_otp.decorators import otp_required
from two_factor.views.utils import class_view_decorator

from tools.models import Organization, OrganizationMember
from tools.user_helpers import CanViewMembersMixin
from tools.view_helpers import OrganizationMemberBreadcrumbsMixin


@class_view_decorator(otp_required)
class OrganizationMemberListView(
    OrganizationMemberBreadcrumbsMixin, CanViewMembersMixin, DetailView
):
    model = Organization
    template_name = "organizations/organization_member_list.html"
    filters_active: List[str] = []

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.filters_active = self.get_filters_active()

    def get_filters_active(self):
        return self.request.GET.getlist("client_status", [])

    def get_checkbox_filters(self):
        return [
            {
                "label": choice[0],
                "value": choice[1],
                "checked": not self.filters_active or choice[0] in self.filters_active,
            }
            for choice in OrganizationMember.STATUSES.choices
        ]

    def get_members(self):
        member_set = self.object.members
        if self.filters_active:
            member_set = member_set.filter(status__in=self.filters_active)

        return member_set.all()

    def build_breadcrumbs(self):
        self.set_breadcrumb_object(self.object)
        return super().build_breadcrumbs()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["members"] = self.get_members()
        context["checkbox_filters"] = self.get_checkbox_filters()
        return context
