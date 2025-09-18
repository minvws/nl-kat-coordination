from enum import Enum

from django.views.generic import TemplateView
from structlog import get_logger

from openkat.mixins import OrganizationPermissionRequiredMixin, OrganizationView
from openkat.view_helpers import OrganizationDetailBreadcrumbsMixin

logger = get_logger(__name__)


class PageActions(Enum):
    RECALCULATE = "recalculate"


class OrganizationSettingsView(
    OrganizationPermissionRequiredMixin, OrganizationDetailBreadcrumbsMixin, OrganizationView, TemplateView
):
    template_name = "organizations/organization_settings.html"
    permission_required = "openkat.view_organization"
