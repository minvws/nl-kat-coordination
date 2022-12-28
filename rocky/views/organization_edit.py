from typing import List, Tuple, Optional

from django.contrib import messages
from django.shortcuts import redirect
from django.urls.base import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import UpdateView
from django_otp.decorators import otp_required
from two_factor.views.utils import class_view_decorator
from django.contrib.auth.mixins import PermissionRequiredMixin
from rocky.settings import MIAUW_API_ENABLED
from account.forms import OrganizationForm
from tools.miauw_helpers import get_registered_usernames
from tools.models import Organization


@class_view_decorator(otp_required)
class OrganizationEditView(PermissionRequiredMixin, UpdateView):
    form_class = OrganizationForm
    model = Organization
    template_name = "organizations/organization_edit.html"
    permission_required = "tools.change_organization"

    def get(self, request, *args, **kwargs):
        if not MIAUW_API_ENABLED:
            messages.add_message(request, messages.WARNING, "Miauw API is not enabled.")
            self.object = self.get_object()
            return redirect(self.get_success_url())

        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if not MIAUW_API_ENABLED:
            self.get(request, *args, **kwargs)

        return super().post(request, *args, **kwargs)

    def get_usernames_input_values(self) -> Optional[List[Tuple[str, str]]]:
        try:
            registered_usernames = get_registered_usernames()
            if registered_usernames is not None:
                return [(username, username) for username in registered_usernames]
        except Exception as e:
            messages.add_message(self.request, messages.WARNING, str(e))

        return None

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"signal_username_choices": self.get_usernames_input_values()})

        return kwargs

    def get_success_url(self):
        return reverse("organization_detail", kwargs={"pk": self.object.id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["breadcrumbs"] = [
            {"url": reverse("organization_list"), "text": "Organizations"},
            {
                "url": reverse("organization_detail", kwargs={"pk": self.object.id}),
                "text": self.object.name,
            },
            {
                "url": reverse("organization_edit", kwargs={"pk": self.object.id}),
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
            return redirect(reverse("organization_detail", kwargs={"pk": organization.id}))

        return redirect("crisis_room")
