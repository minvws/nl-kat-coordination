from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import redirect
from django.urls.base import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import UpdateView
from django_otp.decorators import otp_required
from two_factor.views.utils import class_view_decorator

from account.forms import OrganizationForm
from tools.models import Organization


@class_view_decorator(otp_required)
class OrganizationEditView(PermissionRequiredMixin, UpdateView):
    form_class = OrganizationForm
    model = Organization
    template_name = "organizations/organization_edit.html"
    permission_required = "tools.change_organization"

    def get_success_url(self):
        return reverse("organization_detail", kwargs={"organization_code": self.object.code})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["breadcrumbs"] = [
            {"url": reverse("organization_list"), "text": "Organizations"},
            {
                "url": reverse("organization_detail", kwargs={"organization_code": self.object.id}),
                "text": self.object.name,
            },
            {
                "url": reverse("organization_edit", kwargs={"organization_code": self.object.id}),
                "text": _("Edit"),
            },
        ]

        return context

    def handle_no_permission(self):
        messages.add_message(
            self.request,
            messages.ERROR,
            _("You are not allowed to change organizations."),
        )

        if self.request.user.has_perm("tools.can_view_organization"):
            organization = self.get_object()
            return redirect(reverse("organization_detail", kwargs={"organization_code": organization.id}))

        return redirect("crisis_room")
