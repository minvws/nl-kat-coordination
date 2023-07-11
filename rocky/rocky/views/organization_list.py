from typing import List

from account.models import KATUser
from django.db.models import Count
from django.views.generic import ListView
from tools.models import Organization
from tools.view_helpers import OrganizationBreadcrumbsMixin


class OrganizationListView(
    OrganizationBreadcrumbsMixin,
    ListView,
):
    template_name = "organizations/organization_list.html"

    def get_queryset(self) -> List[Organization]:
        user: KATUser = self.request.user
        return (
            Organization.objects.annotate(member_count=Count("members"))
            .prefetch_related("tags")
            .filter(id__in=[organization.id for organization in user.organizations])
        )
