from datetime import datetime, timezone
from uuid import uuid4
from typing import Type
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView
from django.shortcuts import redirect
from octopoes.api.models import Declaration
from octopoes.models import OOI
from octopoes.models.ooi.findings import MuteFinding
from rocky.views.mixins import OctopoesView
from rocky.bytes_client import get_bytes_client, BytesClient
from rocky.views.mixins import OOIBreadcrumbsMixin
from rocky.views.ooi_view import BaseOOIFormView
from tools.forms.ooi import MuteFindingForm
from tools.view_helpers import get_ooi_url


class MuteFindingView(BaseOOIFormView, OOIBreadcrumbsMixin):
    template_name = "oois/ooi_mute_finding.html"
    ooi_class: Type[OOI] = MuteFinding
    form_class = MuteFindingForm

    def get_ooi_class(self):
        return self.ooi_class

    def get_initial(self):
        initial = super().get_initial()
        initial["finding_id"] = self.request.GET.get("ooi_id", None)
        return initial

    def get_success_url(self):
        ooi_id = self.request.GET.get("ooi_id", None)
        messages.add_message(self.request, messages.SUCCESS, _("OOI {ooi_id} succesfully muted").format(ooi_id=ooi_id))
        return redirect(get_ooi_url("ooi_detail", ooi_id, self.organization.code))
