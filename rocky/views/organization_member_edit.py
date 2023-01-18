from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import redirect
from django.urls.base import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import UpdateView
from django_otp.decorators import otp_required
from two_factor.views.utils import class_view_decorator

from account.forms import OrganizationMemberForm
from rocky.settings import MIAUW_API_ENABLED
from tools.models import OrganizationMember


@class_view_decorator(otp_required)
class OrganizationMemberEditView(PermissionRequiredMixin, UpdateView):
    form_class = OrganizationMemberForm
    model = OrganizationMember
    template_name = "organizations/organization_member_edit.html"
    object: OrganizationMember
    permission_required = "tools.change_organization"

    def get(self, request, *args, **kwargs):
        if not MIAUW_API_ENABLED:
            messages.add_message(request, messages.WARNING, "Miauw API is not enabled.")
            self.object = self.get_object()
            return redirect(
                reverse(
                    "organization_member_list",
                    kwargs={"pk": self.object.organization_id},
                )
            )

        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if not MIAUW_API_ENABLED:
            self.get(request, *args, **kwargs)

        return super().post(request, *args, **kwargs)

    def get_success_url(self):
        return reverse("organization_detail", kwargs={"pk": self.object.organization_id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["breadcrumbs"] = [
            {"url": reverse("organization_list"), "text": "Organizations"},
            {
                "url": reverse("organization_detail", kwargs={"pk": self.object.organization_id}),
                "text": self.object.organization.name,
            },
            {
                "url": reverse("organization_member_edit", kwargs={"pk": self.object.id}),
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
        organization = self.get_object()

        if self.request.user.has_perm("tools.view_organization"):
            return redirect(reverse("organization_detail", kwargs={"pk": organization.id}))

        return redirect("crisis_room")
