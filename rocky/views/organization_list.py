from django.views.generic import ListView
from django_otp.decorators import otp_required
from two_factor.views.utils import class_view_decorator
from django.contrib.auth.mixins import PermissionRequiredMixin
from tools.models import Organization
from tools.view_helpers import OrganizationBreadcrumbsMixin


@class_view_decorator(otp_required)
class OrganizationListView(
    PermissionRequiredMixin,
    OrganizationBreadcrumbsMixin,
    ListView,
):
    model = Organization
    template_name = "organizations/organization_list.html"
    permission_required = "tools.view_organization"

    def get_queryset(self):
        """
        List organization that only belongs to user that requests the list.
        """
        object = self.model.objects.filter(code=self.request.user.organizationmember.organization.code)
        return object

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_organization"] = self.model.objects.get(pk=self.request.session["active_organization_id"])
        return context
