from datetime import datetime, timezone
from time import sleep
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
from account.mixins import OrganizationView


class MuteFindingView(OctopoesView, OOIBreadcrumbsMixin, FormView):
    template_name = "oois/ooi_mute_finding.html"
    ooi_class: Type[OOI] = MuteFinding
    form_class = MuteFindingForm

    def get(self, request, *args, **kwargs):
        # ooi needed for breadcrumbs
        self.ooi = self.get_single_ooi(self.request.GET.get("ooi_id", None), datetime.now(timezone.utc))
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        self.save_ooi(form.cleaned_data)
        sleep(1)
        return super().form_valid(form)

    def get_initial(self):
        initial = super().get_initial()
        initial["finding"] = self.request.GET.get("ooi_id", None)
        return initial

    def save_ooi(self, data) -> None:
        new_ooi = self.ooi_class.parse_obj(data)
        task_id = uuid4()
        declaration = Declaration(ooi=new_ooi, valid_time=datetime.now(timezone.utc), task_id=str(task_id))

        get_bytes_client(self.organization.code).add_manual_proof(
            task_id, BytesClient.raw_from_declarations([declaration])
        )

        self.octopoes_api_connector.save_declaration(declaration)

    def get_success_url(self):
        ooi_id = self.request.GET.get("ooi_id", None)
        messages.add_message(self.request, messages.SUCCESS, _("OOI {ooi_id} succesfully muted").format(ooi_id=ooi_id))
        return redirect(get_ooi_url("ooi_detail", ooi_id, self.organization.code))
