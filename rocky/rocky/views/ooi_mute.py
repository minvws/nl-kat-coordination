from datetime import datetime, timezone
from uuid import uuid4
from typing import Type
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.http import HttpResponseRedirect
from django.views.generic import FormView
from rocky.views.ooi_view import BaseOOIFormView
from rocky.views.mixins import OctopoesView
from rocky.bytes_client import get_bytes_client, BytesClient
from octopoes.api.models import Declaration
from octopoes.models import OOI
from account.mixins import OrganizationView


class MuteObjectView(FormView, OctopoesView):
    ooi_class: Type[OOI] = None
    form_class = None

    def post(self, request, *args, **kwargs):
        ooi_id = request.POST.get("muted_ooi", None)
        if not ooi_id:
            messages.add_message(request, messages.ERROR, _("No OOI ID found. Cannot mute OOI."))
            return super().get(request, *args, **kwargs)
        self.create_ooi(ooi_id)
        return HttpResponseRedirect(self.get_success_url(ooi_id))

    def create_ooi(self, ooi_id) -> OOI:
        observed_at = datetime.now(timezone.utc)
        ooi = self.get_single_ooi(pk=ooi_id, observed_at=observed_at)
        task_id = uuid4()
        declaration = Declaration(ooi=ooi, valid_time=observed_at, task_id=str(task_id))

        get_bytes_client(self.organization.code).add_manual_proof(
            task_id, BytesClient.raw_from_declarations([declaration])
        )

        self.octopoes_api_connector.save_declaration(declaration)

    def get_success_url(self, ooi_id):
        messages.add_message(self.request, messages.SUCCESS, _("OOI {ooi_id} succesfully muted").format(ooi_id=ooi_id))
