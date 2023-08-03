from enum import Enum
from typing import Any

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.views.generic import TemplateView
from django.views.generic.detail import DetailView
from requests.exceptions import RequestException

from account.mixins import OrganizationView


class PageActions(Enum):
    ACCEPT_CLEARANCE = "accept_clearance"
    WITHDRAW_ACCEPTANCE = "withdraw_acceptance"


class OOIClearanceManager(OrganizationView, TemplateView):
    def post(self, request, *args, **kwargs):
        if "action" in self.request.POST:
            self.handle_page_action(request.POST["action"])
        return self.get(request, *args, **kwargs)

    def handle_page_action(self, action: str):
        try:
            if action == PageActions.ACCEPT_CLEARANCE.value:
                self.organization_member.acknowledged_clearance_level = self.organization_member.trusted_clearance_level
            elif action == PageActions.WITHDRAW_ACCEPTANCE.value:
                self.organization_member.acknowledged_clearance_level = -1
            else:
                raise Exception(f"Unhandled allowed action: {action}")
            self.organization_member.save()
        except RequestException as exception:
            messages.add_message(self.request, messages.ERROR, f"{action} failed: '{exception}'")


class AccountView(OOIClearanceManager, DetailView):
    template_name = "account_detail.html"
    context_object_name = "member"

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        self.object = self.get_object()
        return super().get(request, *args, **kwargs)

    def get_object(self):
        return self.organization_member

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {"url": "", "text": "Account details"},
        ]
        return context
