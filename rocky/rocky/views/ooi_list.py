import csv
import json
from datetime import datetime, timezone
from enum import Enum
from typing import List

from django.contrib import messages
from django.http import HttpResponse, Http404, HttpRequest
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django_otp.decorators import otp_required
from django.urls import reverse
from requests import RequestException
from two_factor.views.utils import class_view_decorator
from octopoes.connector import RemoteException
from octopoes.models import Reference, EmptyScanProfile
from octopoes.models.exception import ObjectNotFoundException
from octopoes.models.ooi.findings import Finding, FindingType
from octopoes.models.types import get_collapsed_types, type_by_name
from rocky.exceptions import IndemnificationNotPresentException, ClearanceLevelTooLowException
from rocky.views.ooi_view import BaseOOIListView
from tools.forms.ooi import SelectOOIForm
from tools.models import Indemnification
from tools.enums import CUSTOM_SCAN_LEVEL


class PageActions(Enum):
    DELETE = "delete"
    UPDATE_SCAN_PROFILE = "update-scan-profile"


@class_view_decorator(otp_required)
class OOIListView(BaseOOIListView):
    breadcrumbs = [{"url": reverse_lazy("ooi_list"), "text": _("Objects")}]
    template_name = "oois/ooi_list.html"
    ooi_types = get_collapsed_types().difference({Finding, FindingType})

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.filtered_ooi_types = self.get_filtered_ooi_types()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["types_display"] = self.get_ooi_types_display()
        context["object_type_filters"] = self.get_ooi_type_filters()
        context["select_oois_form"] = SelectOOIForm(
            context.get("ooi_list", []), organization_code=self.organization.code
        )
        context["member"] = self.organization_member
        context["scan_levels"] = [alias for _, alias in CUSTOM_SCAN_LEVEL.choices]
        context["organization_indemnification"] = self.get_organization_indemnification
        context["breadcrumbs"] = [
            {"url": reverse("ooi_list", kwargs={"organization_code": self.organization.code}), "text": _("Objects")},
        ]

        return context

    def get(self, request: HttpRequest, status=200, *args, **kwargs) -> HttpResponse:
        """Override the response status in case submitting a form returns an error message"""
        response = super().get(request, *args, **kwargs)
        response.status_code = status

        return response

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """Perform bulk action on selected oois."""
        selected_oois = request.POST.getlist("ooi")
        if not selected_oois:
            messages.add_message(request, messages.ERROR, _("No OOIs selected."))
            return self.get(request, status=422, *args, **kwargs)

        action = request.POST.get("action")

        if action == PageActions.DELETE.value:
            return self._delete_oois(selected_oois, request, *args, **kwargs)

        if action == PageActions.UPDATE_SCAN_PROFILE.value:
            scan_profile = request.POST.get("scan-profile").lower()
            level = CUSTOM_SCAN_LEVEL[scan_profile]
            if level.value == "inherit":
                return self._set_oois_to_inherit(selected_oois, request, *args, **kwargs)
            return self._set_scan_profiles(selected_oois, level, request, *args, **kwargs)

        messages.add_message(request, messages.ERROR, _("Unknown action."))
        return self.get(request, status=404, *args, **kwargs)

    def _set_scan_profiles(
        self, selected_oois: List[Reference], level: CUSTOM_SCAN_LEVEL, request: HttpRequest, *args, **kwargs
    ) -> HttpResponse:

        try:
            self.verify_raise_clearance_level(level.value)
        except IndemnificationNotPresentException:
            messages.add_message(
                self.request,
                messages.ERROR,
                _(
                    "Could not raise clearance level to L%s. \
                    Indemnification not present at organization %s."
                )
                % (
                    level,
                    self.organization.name,
                ),
            )
            return self.get(request, status=403, *args, **kwargs)
        except ClearanceLevelTooLowException:
            messages.add_message(
                self.request,
                messages.ERROR,
                _(
                    "Could not raise clearance level to L%s. \
                    You acknowledged a clearance level of %s."
                )
                % (
                    level,
                    self.organization_member.acknowledged_clearance_level,
                ),
            )
            return self.get(request, status=403, *args, **kwargs)

        for ooi_reference in selected_oois:
            try:
                self.raise_clearance_level(Reference.from_str(ooi_reference), level.value)
            except (RequestException, RemoteException, ConnectionError):
                messages.add_message(
                    request, messages.ERROR, _("An error occurred while saving clearance level for %s.") % ooi_reference
                )
                return self.get(request, status=500, *args, **kwargs)
            except ObjectNotFoundException:
                messages.add_message(
                    request,
                    messages.ERROR,
                    _("An error occurred while saving clearance level for %s.") % ooi_reference
                    + _("OOI doesn't exist"),
                )
                return self.get(request, status=404, *args, **kwargs)

        messages.add_message(
            request,
            messages.SUCCESS,
            _("Successfully set scan profile to %s for %d oois.") % (level.name, len(selected_oois)),
        )
        return self.get(request, *args, **kwargs)

    def _set_oois_to_inherit(
        self, selected_oois: List[Reference], request: HttpRequest, *args, **kwargs
    ) -> HttpResponse:
        for ooi in selected_oois:
            try:
                self.octopoes_api_connector.save_scan_profile(
                    EmptyScanProfile(reference=Reference.from_str(ooi)),
                    valid_time=datetime.now(timezone.utc),
                )
            except (RequestException, RemoteException, ConnectionError):
                messages.add_message(
                    request,
                    messages.ERROR,
                    _("An error occurred while setting clearance level to inherit for %s.") % ooi,
                )
                return self.get(request, status=500, *args, **kwargs)
            except ObjectNotFoundException:
                messages.add_message(
                    request,
                    messages.ERROR,
                    _("An error occurred while setting clearance level to inherit for %s.") % ooi
                    + _("OOI doesn't exist"),
                )
                return self.get(request, status=404, *args, **kwargs)
        messages.add_message(
            request,
            messages.SUCCESS,
            _("Successfully set %d ooi(s) clearance level to inherit.") % len(selected_oois),
        )
        return self.get(request, *args, **kwargs)

    def _delete_oois(self, selected_oois: List[Reference], request: HttpRequest, *args, **kwargs) -> HttpResponse:
        connector = self.octopoes_api_connector

        for ooi in selected_oois:
            try:
                connector.delete(ooi, valid_time=datetime.now(timezone.utc))
            except (RequestException, RemoteException, ConnectionError):
                messages.add_message(request, messages.ERROR, _("An error occurred deleting %s.") % ooi)
                return self.get(request, status=500, *args, **kwargs)
            except ObjectNotFoundException:
                messages.add_message(
                    request, messages.ERROR, _("An error occurred deleting %s.") % ooi + _("OOI doesn't exist")
                )
                return self.get(request, status=404, *args, **kwargs)

        messages.add_message(
            request,
            messages.SUCCESS,
            _("Successfully deleted %d ooi(s). Note: Bits can recreate objects automatically.") % len(selected_oois),
        )

        return self.get(request, *args, **kwargs)

    def get_organization_indemnification(self):
        return Indemnification.objects.filter(organization=self.organization).exists()


class OOIListExportView(OOIListView):
    def get(self, request, *args, **kwargs):
        super().get(request, *args, **kwargs)

        file_type = request.GET.get("file_type")
        observed_at = self.get_observed_at()
        filters = self.get_ooi_types_display()

        ooi_types = self.ooi_types
        if self.filtered_ooi_types:
            ooi_types = {type_by_name(t) for t in self.filtered_ooi_types}

        ooi_list = self.octopoes_api_connector.list(ooi_types, observed_at).items
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
