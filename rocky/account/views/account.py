from enum import Enum

from django.contrib import messages
from django.views.generic.detail import DetailView
from django_otp.decorators import otp_required
from requests.exceptions import RequestException
from two_factor.views.utils import class_view_decorator

from account.mixins import OrganizationView
from tools.models import OrganizationMember


class PageActions(Enum):
    ACCEPT_CLEARANCE = "accept_clearance"
    WITHDRAW_ACCEPTANCE = "withdraw_acceptance"


@class_view_decorator(otp_required)
class AccountView(OrganizationView, DetailView):
    template_name = "account_detail.html"
    context_object_name = "member"

    def get_object(self):
        return OrganizationMember.objects.get(user=self.request.user, organization=self.organization)

    def post(self, request, *args, **kwargs):
        if "action" in self.request.POST:
            self.handle_page_action(request.POST["action"])
        return self.get(request, *args, **kwargs)

    def handle_page_action(self, action: str):
        try:
            organizationmember = self.get_object()
            if action == PageActions.ACCEPT_CLEARANCE.value:
                organizationmember.acknowledged_clearance_level = organizationmember.trusted_clearance_level
            elif action == PageActions.WITHDRAW_ACCEPTANCE.value:
                organizationmember.acknowledged_clearance_level = 0
            else:
                raise Exception(f"Unhandled allowed action: {action}")
            organizationmember.save()
        except RequestException as exception:
            messages.add_message(self.request, messages.ERROR, f"{action} failed: '{exception}'")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {"url": "", "text": "Account details"},
        ]
        return context
