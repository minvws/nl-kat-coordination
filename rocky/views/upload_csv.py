import csv
import io
from datetime import datetime, timezone
from typing import Dict, ClassVar, Any

from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.urls.base import reverse_lazy
from django.utils.translation import gettext as _
from django.views.generic.edit import FormView
from django_otp.decorators import otp_required
from octopoes.api.models import Declaration
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import Reference
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.network import Network, IPAddressV4, IPAddressV6
from octopoes.models.ooi.web import URL
from pydantic import ValidationError
from two_factor.views.utils import class_view_decorator

from rocky.settings import OCTOPOES_API
from tools.forms.upload_csv import (
    UploadCSVForm,
    CSV_ERRORS,
)

CSV_CRITERIAS = [
    _("Add column titles. Followed by each object on a new line."),
    _(
        "For URL object type, a column 'raw' with URL values is required, starting with http:// or https://, "
        "optionally a second column 'network' is supported "
    ),
    _(
        "For Hostname object type, a column with 'name' values is required, optionally a second column 'network' "
        "is supported "
    ),
    _(
        "For IPAddressV4 and IPAddressV6 object types, a column of 'address' is required, optionally a second column "
        "'network' is supported "
    ),
]


def save_ooi(ooi, organization) -> None:
    connector = OctopoesAPIConnector(OCTOPOES_API, organization)
    connector.save_declaration(Declaration(ooi=ooi, valid_time=datetime.now(timezone.utc)))


@class_view_decorator(otp_required)
class UploadCSV(PermissionRequiredMixin, FormView):
    template_name = "upload_csv.html"
    form_class = UploadCSVForm
    permission_required = "tools.can_scan_organization"
    success_url = reverse_lazy("ooi_list")
    reference_cache: Dict[str, Any] = {"Network": {"internet": Network(name="internet")}}
    ooi_types: ClassVar[Dict[str, Any]] = {
        "Hostname": {"type": Hostname},
        "URL": {"type": URL},
        "Network": {"type": Network, "default": "internet", "argument": "name"},
        "IPAddressV4": {"type": IPAddressV4},
        "IPAddressV6": {"type": IPAddressV6},
    }
    skip_properties = ("object_type", "scan_profile", "primary_key")

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)

        self.organization_code = request.user.organizationmember.organization.code
        if not self.organization_code:
            self.add_error_notification(CSV_ERRORS["no_org"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {"url": reverse("ooi_list"), "text": _("Objects")},
            {"url": reverse("upload_csv"), "text": _("Upload CSV")},
        ]
        context["criterias"] = CSV_CRITERIAS
        return context

    def get_or_create_reference(self, ooi_type_name: str, value: str):
        ooi_type_name = next(filter(lambda x: x.casefold() == ooi_type_name.casefold(), self.ooi_types.keys()))

        # get from cache
        cache = self.reference_cache.setdefault(ooi_type_name, {})
        if value in cache:
            return cache[value]

        ooi_type = self.ooi_types[ooi_type_name]["type"]

        # set default value if any
        if value is None:
            value = self.ooi_types[ooi_type_name].get("default")

        # create the ooi
        kwargs = {self.ooi_types[ooi_type_name]["argument"]: value}
        ooi = ooi_type(**kwargs)
        cache[value] = ooi

        return ooi

    def get_ooi_from_csv(self, ooi_type_name: str, values: Dict[str, str]):
        ooi_type = self.ooi_types[ooi_type_name]["type"]
        ooi_fields = [
            (field, model_field.type_ == Reference, model_field.required)
            for field, model_field in ooi_type.__fields__.items()
            if field not in self.skip_properties
        ]

        kwargs = {}
        for field, is_reference, required in ooi_fields:
            if is_reference and required:
                try:
                    referenced_ooi = self.get_or_create_reference(field, values.get(field))
                    save_ooi(ooi=referenced_ooi, organization=self.organization_code)
                    kwargs[field] = referenced_ooi.reference
                except IndexError:
                    if required:
                        raise IndexError(
                            "Required referenced primary-key field '%s' not set and no default present for Type '%s'."
                            % (field, ooi_type_name)
                        )
                    else:
                        kwargs[field] = None
            else:
                kwargs[field] = values.get(field)

        return ooi_type(**kwargs)

    def form_valid(self, form):
        if not self.proccess_csv(form):
            return redirect("upload_csv")
        return super().form_valid(form)

    def add_error_notification(self, error_message):
        messages.add_message(self.request, messages.ERROR, error_message)
        return False

    def add_success_notification(self, success_message):
        messages.add_message(self.request, messages.SUCCESS, success_message)
        return True

    def proccess_csv(self, form):
        object_type = form.cleaned_data["object_type"]
        csv_file = form.cleaned_data["csv_file"]
        csv_data = io.StringIO(csv_file.read().decode("UTF-8"))
        rows_with_error = []
        try:
            for row_number, row in enumerate(csv.DictReader(csv_data, delimiter=",", quotechar='"'), start=1):
                if not row:
                    continue  # skip empty lines
                try:
                    ooi = self.get_ooi_from_csv(object_type, row)
                    save_ooi(ooi=ooi, organization=self.organization_code)
                except ValidationError:
                    rows_with_error.append(row_number)

            if rows_with_error:
                message = _("Object(s) could not be created for row number(s): ") + ", ".join(map(str, rows_with_error))
                return self.add_error_notification(message)

            self.add_success_notification(_("Object(s) successfully added."))
        except (csv.Error, IndexError):
            return self.add_error_notification(CSV_ERRORS["csv_error"])
