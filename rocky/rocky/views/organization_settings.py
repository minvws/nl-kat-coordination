from datetime import datetime
from enum import Enum

from account.mixins import IndemnificationManagementView, OrganizationPermissionRequiredMixin
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from tools.view_helpers import OrganizationDetailBreadcrumbsMixin


class PageActions(Enum):
    RECALCULATE = "recalculate"


class OrganizationSettingsView(
    OrganizationPermissionRequiredMixin,
    OrganizationDetailBreadcrumbsMixin,
    IndemnificationManagementView,
    TemplateView,
):
    template_name = "organizations/organization_settings.html"
    permission_required = "tools.view_organization"

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """Perform actions based on action type"""
        action = request.POST.get("action")
        if not self.request.user.has_perm("tools.can_recalculate_bits"):
            raise PermissionDenied()
        if action == PageActions.RECALCULATE.value:
            connector = self.octopoes_api_connector

            start_time = datetime.now()
            number_of_bits = connector.recalculate_bits()
            duration = datetime.now() - start_time
            messages.add_message(request, messages.INFO, _(f"Recalculated {number_of_bits} bits. Duration: {duration}"))
            return self.get(request, *args, **kwargs)
        else:
            raise HttpResponseBadRequest("Unknown action")
