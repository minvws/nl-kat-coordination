import logging

from account.forms import OrganizationForm
from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic.edit import CreateView
from tools.models import Organization, OrganizationMember

from rocky.exceptions import ServiceException

logger = logging.getLogger(__name__)


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
        try:
            self.object = form.save()
        except ServiceException as e:
            message = f"An issue occurred in {e.service_name} while creating the organization"
            logger.exception(message)
            messages.add_message(self.request, messages.ERROR, _(message))

            return redirect(self.success_url)  # get_success_url() assumes self.object is set, see ModelFormMixin

        try:
            member, created = OrganizationMember.objects.get_or_create(user=self.request.user, organization=self.object)
            member.acknowledged_clearance_level = 0
            member.trusted_clearance_level = 4
            member.save()
        except Exception:
            message = "An issue occurred while creating the organization"
            logger.exception(message)
            messages.add_message(self.request, messages.ERROR, _(message))

            return redirect(self.success_url)

        self.add_success_notification()
        return redirect(self.get_success_url())

    def add_success_notification(self):
        success_message = _("Organization added successfully.")
        messages.add_message(self.request, messages.SUCCESS, success_message)

    def handle_no_permission(self):
        messages.add_message(self.request, messages.ERROR, _("You are not allowed to add organizations."))
        return redirect("organization_list")
