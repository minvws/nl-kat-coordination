from datetime import datetime, timezone
from typing import Type

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import FormView
from tools.forms.ooi import MuteFindingForm

from octopoes.models import OOI
from octopoes.models.ooi.findings import MutedFinding
from rocky.views.mixins import OctopoesView, OOIBreadcrumbsMixin


class MuteFindingView(PermissionRequiredMixin, OctopoesView, OOIBreadcrumbsMixin, FormView):
    template_name = "oois/ooi_mute_finding.html"
    ooi_class: Type[OOI] = MutedFinding
    form_class = MuteFindingForm
    permission_required = "tools.can_scan_organization"

    def get(self, request, *args, **kwargs):
        # ooi needed for breadcrumbs
        self.ooi = self.get_single_ooi(self.request.GET.get("ooi_id", None), datetime.now(timezone.utc))
        return super().get(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        initial["finding"] = self.request.GET.get("ooi_id", None)
        initial["ooi_type"] = self.ooi_class.__name__
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ooi_type"] = self.ooi_class.__name__
        context["finding"] = self.ooi
        return context
