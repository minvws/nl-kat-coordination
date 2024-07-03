from datetime import datetime, timezone
from enum import Enum
from typing import Any, TypeAlias
from urllib.parse import unquote

from account.mixins import OrganizationPermissionRequiredMixin, OrganizationView
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.urls.base import reverse_lazy
from django.utils.translation import gettext as _
from django.views.generic.edit import FormView
from httpx import HTTPError, HTTPStatusError
from tools.forms.upload_raw import UploadRawForm

from octopoes.models import OOI, PrimaryKeyToken, Reference
from octopoes.models.types import OOI_TYPES
from rocky.bytes_client import get_bytes_client

SerializedOOIValue: TypeAlias = None | str | int | float | dict[str, str | PrimaryKeyToken] | list["SerializedOOIValue"]
SerializedOOI: TypeAlias = dict[str, SerializedOOIValue]


def _serialize_value(value: Any, required: bool) -> SerializedOOIValue:
    if isinstance(value, list):
        return [_serialize_value(item, required) for item in value]
    if isinstance(value, Reference):
        try:
            return value.tokenized.root
        except AttributeError:
            if required:
                raise

            return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, int | float):
        return value
    else:
        return str(value)


def serialize_ooi(ooi: OOI) -> SerializedOOI:
    serialized_oois = {}
    for key, value in ooi:
        if key not in ooi.model_fields:
            continue
        serialized_oois[key] = _serialize_value(value, ooi.model_fields[key].is_required())
    return serialized_oois


class UploadRaw(OrganizationPermissionRequiredMixin, OrganizationView, FormView):
    template_name = "upload_raw.html"
    form_class = UploadRawForm
    permission_required = "tools.can_scan_organization"

    def get_initial(self):
        """
        Returns the initial data to use for forms on this view.
        """
        initial = super().get_initial()
        if "mime_type" in self.kwargs:
            initial["mime_types"] = unquote(self.kwargs["mime_type"])
        elif "mime_types" in self.kwargs:
            initial["mime_types"] = unquote(self.kwargs["mime_types"])
        return initial

    def get_success_url(self):
        return reverse_lazy("ooi_list", kwargs={"organization_code": self.organization.code})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {"url": reverse("ooi_list", kwargs={"organization_code": self.organization.code}), "text": _("Objects")},
            {
                "url": reverse("upload_raw", kwargs={"organization_code": self.organization.code}),
                "text": _("Upload raw"),
            },
        ]
        return context

    def form_valid(self, form):
        if not self.process_raw(form):
            return redirect("upload_raw", organization_code=self.organization.code)
        return super().form_valid(form)

    def add_error_notification(self, error_message):
        messages.add_message(self.request, messages.ERROR, error_message)
        return False

    def add_success_notification(self, success_message):
        messages.add_message(self.request, messages.SUCCESS, success_message)
        return True

    def process_raw(self, form):
        raw_file = form.cleaned_data["raw_file"]
        mime_types = form.cleaned_data["mime_types"]
        input_ooi = form.cleaned_data["ooi"]

        try:
            get_bytes_client(self.organization.code).upload_raw(
                raw_file.read(), mime_types, input_ooi=input_ooi.primary_key, input_dict=serialize_ooi(input_ooi)
            )
        except HTTPStatusError as exc:
            return self.add_error_notification(
                _("Raw file could not be uploaded to Bytes: status code %d") % exc.response.status_code
            )
        except HTTPError as exc:
            return self.add_error_notification(_("Raw file could not be uploaded to Bytes: %s") % str(exc))
        else:
            self.add_success_notification(_("Raw file successfully added."))

    def get_form_kwargs(self):
        kwargs = {
            "connector": self.octopoes_api_connector,
            "ooi_list": self.get_ooi_options(),
        }
        kwargs.update(super().get_form_kwargs())

        if "ooi_class" in kwargs:
            del kwargs["ooi_class"]

        return kwargs

    def get_ooi_options(self) -> list[tuple[str, str]]:
        objects = self.octopoes_api_connector.list_objects(
            OOI_TYPES.values(), valid_time=datetime.now(timezone.utc)
        ).items

        # generate options
        options = [(o.primary_key, o.get_ooi_type()) for o in objects]

        return options
