from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.urls.base import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import UpdateView
from django_otp.decorators import otp_required
from two_factor.views.utils import class_view_decorator
from account.forms import OrganizationMemberEditForm
from tools.models import OrganizationMember
from account.mixins import OrganizationView


@class_view_decorator(otp_required)
class OrganizationMemberEditView(PermissionRequiredMixin, UserPassesTestMixin, OrganizationView, UpdateView):
    form_class = OrganizationMemberEditForm
    model = OrganizationMember
    template_name = "organizations/organization_member_edit.html"
    object: OrganizationMember
    permission_required = "tools.change_organizationmember"

    def test_func(self):
        return not self.get_object().user.is_superuser or self.request.user.is_superuser

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

    def form_valid(self, form):
        tcl = form.cleaned_data["trusted_clearance_level"]
        acl = form.cleaned_data["acknowledged_clearance_level"]

        if (not tcl or not acl) and int(tcl) < int(acl):
            messages.add_message(
                self.request,
                messages.WARNING,
                _(
                    "The updated trusted clearance level of L%s is lower then the member's acknowledged clearance level of L%s. This member only has clearance for level L%s. For this reason the acknowldeged clearance level has been set at the same level as trusted clearance level."
                )
                % (tcl, acl, tcl),
            )
        return super().form_valid(form)
