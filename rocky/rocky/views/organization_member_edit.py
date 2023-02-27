from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import redirect
from django.urls.base import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import UpdateView
from django_otp.decorators import otp_required
from two_factor.views.utils import class_view_decorator
from account.forms import OrganizationMemberEditForm
from tools.models import OrganizationMember
from account.mixins import OrganizationView


@class_view_decorator(otp_required)
class OrganizationMemberEditView(PermissionRequiredMixin, OrganizationView, UpdateView):
    form_class = OrganizationMemberEditForm
    model = OrganizationMember
    template_name = "organizations/organization_member_edit.html"
    object: OrganizationMember
    permission_required = "tools.change_organizationmember"

    def get_success_url(self):
        messages.add_message(
            self.request,
            messages.SUCCESS,
            _("Member %s successfully updated.") % (self.object.member_name),
        )
        return reverse("organization_detail", kwargs={"organization_code": self.organization.code})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["breadcrumbs"] = [
            {"url": reverse("organization_list"), "text": "Organizations"},
            {
                "url": reverse(
                    "organization_member_edit",
                    kwargs={"organization_code": self.organization.code, "pk": self.object.id},
                ),
                "text": _("Edit member"),
            },
        ]

        return context

    def handle_no_permission(self):
        messages.add_message(
            self.request,
            messages.ERROR,
            _("You are not allowed to edit organization members."),
        )
        return redirect(reverse("organization_detail", kwargs={"organization_code": self.organization.code}))
