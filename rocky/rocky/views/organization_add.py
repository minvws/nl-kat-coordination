from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic.edit import CreateView
from django_otp.decorators import otp_required
from two_factor.views.utils import class_view_decorator

from account.forms import OrganizationForm
from tools.models import Organization, OrganizationMember


@class_view_decorator(otp_required)
class OrganizationAddView(PermissionRequiredMixin, CreateView):
    """
    View to create a new organization
    """

    model = Organization
    template_name = "organizations/organization_add.html"
    form_class = OrganizationForm
    success_url = reverse_lazy("organization_list")
    permission_required = "tools.add_organization"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {"url": reverse("organization_list"), "text": _("Organizations")},
            {"url": reverse("organization_add"), "text": _("Setup")},
        ]
        return context

    def form_valid(self, form):
        self.object = form.save()
        OrganizationMember.objects.get_or_create(user=self.request.user, organization=self.object)
        self.add_success_notification()
        return super().form_valid(form)

    def add_success_notification(self):
        success_message = _("Organization added succesfully.")
        messages.add_message(self.request, messages.SUCCESS, success_message)

    def handle_no_permission(self):
        messages.add_message(self.request, messages.ERROR, _("You are not allowed to add organizations."))
        return redirect("organization_list")
