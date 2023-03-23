from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.urls.base import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import UpdateView
from django_otp.decorators import otp_required
from two_factor.views.utils import class_view_decorator

from account.forms import OrganizationUpdateForm
from tools.models import Organization


@class_view_decorator(otp_required)
class OrganizationEditView(PermissionRequiredMixin, UpdateView):
    form_class = OrganizationUpdateForm
    model = Organization
    template_name = "organizations/organization_edit.html"
    permission_required = "tools.change_organization"

    def get_success_url(self):
        messages.add_message(
            self.request,
            messages.SUCCESS,
            _("Organization %s successfully updated.") % (self.object.name),
        )
        return reverse("organization_detail", kwargs={"organization_code": self.object.code})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["breadcrumbs"] = [
            {"url": reverse("organization_list"), "text": "Organizations"},
            {
                "url": reverse("organization_detail", kwargs={"organization_code": self.object.code}),
                "text": self.object.name,
            },
            {
                "url": reverse(
                    "organization_edit", kwargs={"organization_code": self.object.code, "pk": self.object.id}
                ),
                "text": _("Edit"),
            },
        ]

        return context
