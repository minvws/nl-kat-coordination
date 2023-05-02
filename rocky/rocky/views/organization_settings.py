from enum import Enum

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpRequest, HttpResponse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from django_otp.decorators import otp_required
from tools.view_helpers import OrganizationDetailBreadcrumbsMixin
from two_factor.views.utils import class_view_decorator


class PageActions(Enum):
    RECALCULATE = "recalculate"


@class_view_decorator(otp_required)
class OrganizationSettingsView(OrganizationDetailBreadcrumbsMixin, TemplateView):
    template_name = "organizations/organization_settings.html"

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """Perform actions based on action type"""
        action = request.POST.get("action")
        if not self.request.user.has_perm("tools.recalculate_bits"):
            raise PermissionDenied()
        if action == PageActions.RECALCULATE.value:
            connector = self.octopoes_api_connector
            number_of_bits = connector.recalculate_bits()
            messages.add_message(request, messages.INFO, _(f"Racalculated {number_of_bits} bits."))
            return self.get(request, *args, **kwargs)
        else:
            raise Http404()
