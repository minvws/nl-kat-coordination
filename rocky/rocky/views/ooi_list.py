import csv
import json
from datetime import datetime, timezone
from enum import Enum
from typing import List

from django.contrib import messages
from django.http import Http404, HttpRequest, HttpResponse
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from requests import RequestException
from tools.enums import CUSTOM_SCAN_LEVEL
from tools.forms.ooi import SelectOOIForm
from tools.view_helpers import get_mandatory_fields

from octopoes.connector import RemoteException
from octopoes.models import Reference
from octopoes.models.exception import ObjectNotFoundException
from rocky.views.mixins import OOIList
from rocky.views.ooi_view import BaseOOIListView


class PageActions(Enum):
    DELETE = "delete"
    UPDATE_SCAN_PROFILE = "update-scan-profile"


class OOIListView(BaseOOIListView):
    breadcrumbs = [{"url": reverse_lazy("ooi_list"), "text": _("Objects")}]
    template_name = "oois/ooi_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["types_display"] = self.get_ooi_types_display()
        context["object_type_filters"] = self.get_ooi_type_filters()
        context["observed_at"] = self.get_observed_at()
        context["mandatory_fields"] = get_mandatory_fields(self.request, params=["observed_at"])
        context["select_oois_form"] = SelectOOIForm(
            context.get("ooi_list", []), organization_code=self.organization.code
        )

        context["scan_levels"] = [alias for _, alias in CUSTOM_SCAN_LEVEL.choices]
        context["breadcrumbs"] = [
            {"url": reverse("ooi_list", kwargs={"organization_code": self.organization.code}), "text": _("Objects")},
        ]

        return context

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """Perform bulk action on selected oois."""
        selected_oois = request.POST.getlist("ooi", None)
        action = request.POST.get("action", None)
        scan_profile = request.POST.get("scan-profile", None)
        level = CUSTOM_SCAN_LEVEL[str(scan_profile).upper()]

        if action == PageActions.DELETE.value:
            return self._delete_oois(selected_oois, request, *args, **kwargs)
        if action == PageActions.UPDATE_SCAN_PROFILE.value:
            self.change_clearance_level(selected_oois, level.value)
        return self.get(request, *args, **kwargs)

    def _delete_oois(self, selected_oois: List[Reference], request: HttpRequest, *args, **kwargs) -> HttpResponse:
        connector = self.octopoes_api_connector
        valid_time = datetime.now(timezone.utc)

        try:
            connector.delete_many(selected_oois, valid_time)
        except (RequestException, RemoteException, ConnectionError):
            messages.add_message(request, messages.ERROR, _("An error occurred while deleting oois."))
            return self.get(request, status=500, *args, **kwargs)
        except ObjectNotFoundException:
            messages.add_message(
                request, messages.ERROR, _("An error occurred while deleting oois: one of the OOIs doesn't exist.")
            )
            return self.get(request, status=404, *args, **kwargs)

        messages.add_message(
            request,
            messages.SUCCESS,
            _("Successfully deleted %d ooi(s). Note: Bits can recreate objects automatically.") % len(selected_oois),
        )

        return self.get(request, *args, **kwargs)


class OOIListExportView(BaseOOIListView):
    def get(self, request, *args, **kwargs):
        file_type = request.GET.get("file_type")
        observed_at = self.get_observed_at()
        filters = self.get_ooi_types_display()

        queryset = self.get_queryset()
        ooi_list = queryset[: OOIList.HARD_LIMIT]

        exports = [
            {
                "observed_at": str(observed_at),
                "filters": str(filters),
            }
        ]

        for ooi in ooi_list:
            exports.append(
                {
                    "key": ooi.primary_key,
                    "name": ooi.human_readable,
                    "ooi_type": ooi.ooi_type,
                }
            )

        if file_type == "json":
            response = HttpResponse(
                json.dumps(exports),
                content_type="application/json",
                headers={"Content-Disposition": "attachment; filename=ooi_list_" + str(observed_at) + ".json"},
            )

            return response

        elif file_type == "csv":
            response = HttpResponse(
                content_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=ooi_list_" + str(observed_at) + ".csv"},
            )

            writer = csv.writer(response)
            writer.writerow(["observed_at", "filters"])
            writer.writerow([str(observed_at), str(filters)])
            writer.writerow(["key", "name", "ooi_type"])
            for ooi in ooi_list:
                writer.writerow(
                    [
                        ooi.primary_key,
                        ooi.human_readable,
                        ooi.ooi_type,
                    ]
                )

            return response

        else:
            raise Http404("Export type not found")
