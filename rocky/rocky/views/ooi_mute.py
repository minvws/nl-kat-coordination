from account.mixins import OrganizationPermissionRequiredMixin
from django.views.generic import FormView
from tools.forms.ooi import MuteFindingForm

from octopoes.models.ooi.findings import MutedFinding
from rocky.views.ooi_view import BaseOOIDetailView


class MuteFindingView(OrganizationPermissionRequiredMixin, BaseOOIDetailView, FormView):
    template_name = "oois/ooi_mute_finding.html"
    form_class = MuteFindingForm
    permission_required = "tools.can_scan_organization"
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
