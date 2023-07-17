from account.mixins import OrganizationPermissionRequiredMixin
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView
from tools.forms.ooi import MuteFindingForm
from tools.ooi_helpers import create_ooi

from octopoes.models.ooi.findings import MutedFinding
from rocky.views.mixins import SingleOOIMixin
from rocky.views.ooi_view import BaseOOIDetailView


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


class MuteFindingsBulkView(OrganizationPermissionRequiredMixin, SingleOOIMixin):
    ooi_class = MutedFinding
    permission_required = "tools.can_mute_findings"

    def post(self, request, *args, **kwargs):
        selected_findings = request.POST.getlist("finding", None)
        reason = request.POST.get("reason", None)

        if not selected_findings:
            messages.add_message(self.request, messages.WARNING, _("Please select at least one finding."))
            return redirect(reverse("finding_list", kwargs={"organization_code": self.organization.code}))

        for finding in selected_findings:
            ooi = self.ooi_class.parse_obj({"finding": finding, "reason": reason})
            create_ooi(self.octopoes_api_connector, self.bytes_client, ooi)

        messages.add_message(self.request, messages.SUCCESS, _("Finding(s) successfully muted."))
        return redirect(reverse("finding_list", kwargs={"organization_code": self.organization.code}))
