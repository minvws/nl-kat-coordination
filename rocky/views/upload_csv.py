from datetime import datetime, timezone
import csv
import io
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic.edit import FormView
from django.utils.translation import gettext as _
from django.urls.base import reverse_lazy
from django.urls import reverse
from django.shortcuts import redirect
from django.contrib import messages
from pydantic import ValidationError
from django_otp.decorators import otp_required
from two_factor.views.utils import class_view_decorator
from octopoes.api.models import Declaration
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.web import URL
from octopoes.models.ooi.network import Network, IPAddressV4, IPAddressV6
from octopoes.connector.octopoes import OctopoesAPIConnector
from rocky.settings import OCTOPOES_API
from tools.forms.upload_csv import (
    UploadCSVForm,
    CSV_ERRORS,
)

CSV_CRITERIAS = [
    _(
        "Do not add column titles and only 1 column is required. Each value on a new line."
    ),
    _(
        "For URL object type, a column with URL values is required, starting with http:// or https://"
    ),
    _("For Hostname object type, a column with hostnames values is required."),
    _(
        "For IPAddressV4 and IPAddressV6 object types, a column of ip addresses is required."
    ),
]


@class_view_decorator(otp_required)
class UploadCSV(PermissionRequiredMixin, FormView):
    template_name = "upload_csv.html"
    form_class = UploadCSVForm
    permission_required = "tools.can_scan_organization"
    success_url = reverse_lazy("ooi_list")
    network = Network(name="internet")

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.organization_code = request.user.organizationmember.organization.code
        if not self.organization_code:
            self.add_error_notification(CSV_ERRORS["no_org"])
        else:
            # First create the Network object itself
            self._save_ooi(ooi=self.network, organization=self.organization_code)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {"url": reverse("ooi_list"), "text": _("Objects")},
            {"url": reverse("upload_csv"), "text": _("Upload CSV")},
        ]
        context["criterias"] = CSV_CRITERIAS
        return context

    def get_ooi_from_csv(self, ooi_type: str, value: str):
        ooi = None
        if ooi_type == "Hostname":
            ooi = Hostname(name=value, network=self.network.reference)
        if ooi_type == "URL":
            ooi = URL(raw=value, network=self.network.reference)
        if ooi_type == "IPAddressV4":
            ooi = IPAddressV4(address=value, network=self.network.reference)
        if ooi_type == "IPAddressV6":
            ooi = IPAddressV6(address=value, network=self.network.reference)
        return ooi

    def _save_ooi(self, ooi, organization) -> None:
        connector = OctopoesAPIConnector(OCTOPOES_API, organization)
        connector.save_declaration(
            Declaration(ooi=ooi, valid_time=datetime.now(timezone.utc))
        )

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
            for rownumber, row in enumerate(
                csv.reader(csv_data, delimiter=",", quotechar='"')
            ):
                rownumber += 1  # start at 1 and not 0
                if len(row) == 1:
                    object_type_value = row[0]
                    try:
                        ooi = self.get_ooi_from_csv(object_type, object_type_value)
                        self._save_ooi(ooi=ooi, organization=self.organization_code)
                    except ValidationError:
                        rows_with_error.append(str(rownumber))
                else:
                    return self.add_error_notification(CSV_ERRORS["bad_columns"])
            if rows_with_error:
                message = _(
                    "Object(s) could not be created for line number(s): "
                ) + ", ".join(rows_with_error)
                return self.add_error_notification(message)
            else:
                self.add_success_notification(_("Object(s) successfully added."))
        except (csv.Error, IndexError):
            return self.add_error_notification(CSV_ERRORS["csv_error"])
