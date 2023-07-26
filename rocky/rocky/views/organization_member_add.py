from typing import Any

from account.forms import AccountTypeSelectForm, MemberRegistrationForm
from account.mixins import OrganizationPermissionRequiredMixin
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.urls.base import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic.edit import FormView
from tools.view_helpers import OrganizationMemberBreadcrumbsMixin

from rocky.messaging import clearance_level_warning_dns_report

User = get_user_model()


class OrganizationMemberAddAccountTypeView(
    OrganizationPermissionRequiredMixin, OrganizationMemberBreadcrumbsMixin, FormView
):
    """
    View to create a new member starting with choosing the account type.
    """

    template_name = "organizations/organization_member_add_account_type.html"
    permission_required = "tools.add_organizationmember"
    form_class = AccountTypeSelectForm

    def get(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        account_type = self.request.GET.get("account_type", None)
        if not account_type:
            return super().get(request, *args, **kwargs)
        return redirect(
            reverse(
                "organization_member_add",
                kwargs={"organization_code": self.organization.code, "account_type": account_type},
            )
        )

    def build_breadcrumbs(self):
        breadcrumbs = super().build_breadcrumbs()
        breadcrumbs.append(
            {
                "url": reverse(
                    "organization_member_add_account_type",
                    kwargs={"organization_code": self.organization.code},
                ),
                "text": _("Add Account Type"),
            },
        )
        return breadcrumbs


class OrganizationMemberAddView(OrganizationPermissionRequiredMixin, OrganizationMemberBreadcrumbsMixin, FormView):
    """
    View to create a new member.
    """

    template_name = "organizations/organization_member_add.html"
    form_class = MemberRegistrationForm
    permission_required = "tools.add_organizationmember"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.organization
        kwargs["account_type"] = self.kwargs["account_type"]
        return kwargs

    def form_valid(self, form):
        trusted_clearance_level = form.cleaned_data.get("trusted_clearance_level")
        if trusted_clearance_level and int(trusted_clearance_level) < 2:
            clearance_level_warning_dns_report(self.request, trusted_clearance_level)
        self.add_success_notification()
        return super().form_valid(form)

    def add_success_notification(self):
        success_message = _("Member added successfully.")
        messages.add_message(self.request, messages.SUCCESS, success_message)

    def get_success_url(self, **kwargs):
        return reverse_lazy("organization_member_list", kwargs={"organization_code": self.organization.code})

    def build_breadcrumbs(self):
        breadcrumbs = super().build_breadcrumbs()
        breadcrumbs.extend(
            [
                {
                    "url": reverse(
                        "organization_member_add_account_type",
                        kwargs={"organization_code": self.organization.code},
                    ),
                    "text": _("Add Account Type"),
                },
                {
                    "url": reverse(
                        "organization_member_add",
                        kwargs={
                            "organization_code": self.organization.code,
                            "account_type": self.kwargs["account_type"],
                        },
                    ),
                    "text": _("Add Member"),
                },
            ]
        )
        return breadcrumbs
