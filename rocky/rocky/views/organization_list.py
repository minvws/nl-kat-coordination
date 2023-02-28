from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import ListView
from django_otp.decorators import otp_required
from two_factor.views.utils import class_view_decorator

from tools.models import Organization, OrganizationMember
from tools.view_helpers import OrganizationBreadcrumbsMixin


@class_view_decorator(otp_required)
class OrganizationListView(
    PermissionRequiredMixin,
    OrganizationBreadcrumbsMixin,
    ListView,
):
    template_name = "organizations/organization_list.html"
    permission_required = "tools.view_organization"

    def get_organizationmembers(self, organization):
        return OrganizationMember.objects.filter(organization=organization)

    def get_user_queryset(self):
        queryset = []
        members = OrganizationMember.objects.filter(user=self.request.user)
        for member in members:
            queryset.append(
                {
                    "organization": member.organization,
                    "total_members": self.get_organizationmembers(member.organization).count(),
                }
            )
        return queryset

    def get_superuser_queryset(self):
        queryset = []
        organizations = Organization.objects.all()
        for organization in organizations:
            members = self.get_organizationmembers(organization)
            queryset.append({"organization": organization, "total_members": members.count()})
        return queryset

    def get_queryset(self):
        if self.request.user.is_superuser:
            return self.get_superuser_queryset()
        return self.get_user_queryset()
