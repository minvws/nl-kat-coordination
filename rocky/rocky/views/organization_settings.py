from account.mixins import OrganizationPermissionRequiredMixin
from django.views.generic import TemplateView
from django_otp.decorators import otp_required
from tools.view_helpers import OrganizationDetailBreadcrumbsMixin
from two_factor.views.utils import class_view_decorator


@class_view_decorator(otp_required)
class OrganizationSettingsView(OrganizationPermissionRequiredMixin, OrganizationDetailBreadcrumbsMixin, TemplateView):
    template_name = "organizations/organization_settings.html"
    permission_required = "tools.view_organization"
