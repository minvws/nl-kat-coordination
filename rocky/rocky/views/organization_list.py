from typing import List

from account.models import KATUser
from account.mixins import RockyPermissionRequiredMixin
from django.db.models import Count
from django.views.generic import ListView
from django_otp.decorators import otp_required
from tools.models import Organization
from tools.view_helpers import OrganizationBreadcrumbsMixin
from two_factor.views.utils import class_view_decorator


@class_view_decorator(otp_required)
class OrganizationListView(
    RockyPermissionRequiredMixin,
    OrganizationBreadcrumbsMixin,
    ListView,
):
    template_name = "organizations/organization_list.html"
    permission_required = "view_organization"

    def get_queryset(self) -> List[Organization]:
        user: KATUser = self.request.user
        return (
            Organization.objects.annotate(member_count=Count("members"))
            .prefetch_related("tags")
            .filter(id__in=[organization.id for organization in user.organizations])
        )
