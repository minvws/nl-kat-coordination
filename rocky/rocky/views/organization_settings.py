from django.contrib import messages
from django.views.generic import TemplateView
from django.utils.translation import gettext_lazy as _
from django_otp.decorators import otp_required
from tools.view_helpers import OrganizationDetailBreadcrumbsMixin
from two_factor.views.utils import class_view_decorator


@class_view_decorator(otp_required)
class OrganizationSettingsView(OrganizationDetailBreadcrumbsMixin, TemplateView):
    template_name = "organizations/organization_settings.html"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        if not self.indemnification_present:
            messages.add_message(self.request, messages.ERROR, _("Indemnification is not set for this organization."))
