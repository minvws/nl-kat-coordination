from django.db.models import Count, QuerySet
from django.views.generic import ListView
from structlog import get_logger

from account.models import KATUser
from openkat.models import Organization
from openkat.view_helpers import OrganizationBreadcrumbsMixin

logger = get_logger(__name__)


class OrganizationListView(OrganizationBreadcrumbsMixin, ListView):
    template_name = "organizations/organization_list.html"

    def get_queryset(self) -> QuerySet[Organization]:
        user: KATUser = self.request.user
        return (
            Organization.objects.annotate(member_count=Count("members"))
            .prefetch_related("tags")
            .filter(id__in=[organization.id for organization in user.organizations])
        )
