from account.mixins import OrganizationPermissionRequiredMixin
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView
from tools.forms.ooi import MuteFindingForm

from octopoes.models.ooi.findings import MutedFinding
from rocky.views.ooi_view import BaseOOIDetailView, OOICreateView


class MuteFindingView(OrganizationPermissionRequiredMixin, BaseOOIDetailView, FormView):
    template_name = "oois/ooi_mute_finding.html"
    form_class = MuteFindingForm
    permission_required = "tools.can_mute_findings"
    depth = 1

    def get_initial(self):
        initial = super().get_initial()
        initial["finding"] = self.ooi.reference
        initial["ooi_type"] = MutedFinding.get_object_type()

        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ooi_type"] = MutedFinding.get_object_type()

        return context


class MuteFindingsBulkView(OOICreateView):
    def post(self, request, *args, **kwargs):
        self.ooi_class = MutedFinding
        selected_findings = request.POST.getlist("finding", None)
        reason = request.POST.get("reason", None)
        if not selected_findings:
            messages.add_message(self.request, messages.WARNING, _("Please select at least one finding."))
        for finding in selected_findings:
            data = {"finding": finding, "reason": reason}
            self.save_ooi(data)
        messages.add_message(self.request, messages.SUCCESS, _("Finding(s) successfully muted."))
        return redirect(reverse("finding_list", kwargs={"organization_code": self.organization.code}))
