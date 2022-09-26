from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django_otp.decorators import otp_required
from two_factor.views.utils import class_view_decorator
from django.contrib import messages
from django.views.generic.edit import CreateView
from django.contrib.auth import get_user_model
from tools.models import Organization
from account.forms import OrganizationMemberToGroupAddForm
from tools.view_helpers import OrganizationMemberBreadcrumbsMixin
from django.contrib.auth.mixins import PermissionRequiredMixin, UserPassesTestMixin

User = get_user_model()


@class_view_decorator(otp_required)
class OrganizationMemberAddView(
    UserPassesTestMixin,
    PermissionRequiredMixin,
    OrganizationMemberBreadcrumbsMixin,
    CreateView,
):
    """
    View to create a new organization
    """

    model = User
    template_name = "organizations/organization_member_add.html"
    form_class = OrganizationMemberToGroupAddForm
    permission_required = "tools.add_organizationmember"

    def test_func(self):
        """
        Cannot add member to an organization where user is not part of.
        """
        organization = Organization.objects.filter(pk=self.kwargs["pk"])
        return self.request.user.organizationmember.organization in organization

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization_id"] = self.kwargs["pk"]
        return kwargs

    def get_success_url(self, **kwargs):
        return reverse_lazy(
            "organization_member_list", kwargs={"pk": self.kwargs["pk"]}
        )

    def build_breadcrumbs(self):
        self.set_breadcrumb_object(self.get_organization())
        breadcrumbs = super().build_breadcrumbs()
        breadcrumbs.append(
            {
                "url": reverse(
                    "organization_member_add", kwargs={"pk": self.kwargs["pk"]}
                ),
                "text": _("Create"),
            }
        )
        return breadcrumbs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["organization"] = self.get_organization()
        return context

    def get_organization(self):
        return Organization.objects.get(pk=self.kwargs["pk"])

    def form_valid(self, form):
        self.add_success_notification()
        return super().form_valid(form)

    def add_success_notification(self):
        success_message = _("Member added succesfully.")
        messages.add_message(self.request, messages.SUCCESS, success_message)

    def handle_no_permission(self):
        messages.add_message(
            self.request,
            messages.ERROR,
            _("You are not allowed to add organization members."),
        )
        organization = self.get_object()
        return redirect(reverse("organization_detail", kwargs={"pk": organization.id}))
