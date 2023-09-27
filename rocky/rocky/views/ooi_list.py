import csv
import json
from datetime import datetime, timezone
from enum import Enum
from typing import List

from django.contrib import messages
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from requests import RequestException
from tools.enums import CUSTOM_SCAN_LEVEL
from tools.forms.ooi import SelectOOIForm
from tools.forms.ooi_form import OOITypeMultiCheckboxForm
from tools.models import Indemnification
from tools.view_helpers import get_mandatory_fields

from octopoes.connector import RemoteException
from octopoes.models import EmptyScanProfile, Reference
from octopoes.models.exception import ObjectNotFoundException
from rocky.exceptions import (
    AcknowledgedClearanceLevelTooLowException,
    IndemnificationNotPresentException,
    TrustedClearanceLevelTooLowException,
)
from rocky.views.mixins import OctopoesView, OOIList
from rocky.views.ooi_view import BaseOOIListView


class PageActions(Enum):
    DELETE = "delete"
    UPDATE_SCAN_PROFILE = "update-scan-profile"


class OOIListView(BaseOOIListView, OctopoesView):
    breadcrumbs = [{"url": reverse_lazy("ooi_list"), "text": _("Objects")}]
    template_name = "oois/ooi_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["active_filters"] = self.get_active_filters()
        context["ooi_type_form"] = OOITypeMultiCheckboxForm(self.request.GET)
        context["observed_at"] = self.get_observed_at()
        context["mandatory_fields"] = get_mandatory_fields(self.request, params=["observed_at"])
        context["select_oois_form"] = SelectOOIForm(
            context.get("ooi_list", []),
            organization_code=self.organization.code,
            mandatory_fields=context["mandatory_fields"],
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
            scan_profile = request.POST.get("scan-profile")
            level = CUSTOM_SCAN_LEVEL[str(scan_profile).upper()]
            if level.value == "inherit":
                return self._set_oois_to_inherit(selected_oois, request, *args, **kwargs)
            return self._set_scan_profiles(selected_oois, level, request, *args, **kwargs)

        messages.add_message(request, messages.ERROR, _("Unknown action."))
        return self.get(request, status=404, *args, **kwargs)

    def _set_scan_profiles(
        self, selected_oois: List[Reference], level: CUSTOM_SCAN_LEVEL, request: HttpRequest, *args, **kwargs
    ) -> HttpResponse:
        try:
            self.raise_clearance_levels(selected_oois, level.value)
        except IndemnificationNotPresentException:
            messages.add_message(
                self.request,
                messages.ERROR,
                _("Could not raise clearance levels to L%s. Indemnification not present at organization %s.")
                % (
                    level,
                    self.organization.name,
                ),
            )
            return self.get(request, status=403, *args, **kwargs)
        except TrustedClearanceLevelTooLowException:
            messages.add_message(
                self.request,
                messages.ERROR,
                _(
                    "Could not raise clearance level to L%s. "
                    "You were trusted a clearance level of L%s. "
                    "Contact your administrator to receive a higher clearance."
                )
                % (
                    level,
                    self.organization_member.trusted_clearance_level,
                ),
            )
            return self.get(request, status=403, *args, **kwargs)
        except AcknowledgedClearanceLevelTooLowException:
            messages.add_message(
                self.request,
                messages.ERROR,
                _(
                    "Could not raise clearance level to L%s. "
                    "You acknowledged a clearance level of L%s. "
                    "Please accept the clearance level below to proceed."
                )
                % (
                    level,
                    self.organization_member.acknowledged_clearance_level,
                ),
            )
            return redirect(reverse("account_detail", kwargs={"organization_code": self.organization.code}))

        except (RequestException, RemoteException, ConnectionError):
            messages.add_message(request, messages.ERROR, _("An error occurred while saving clearance levels."))

            return self.get(request, status=500, *args, **kwargs)
        except ObjectNotFoundException:
            messages.add_message(
                request,
                messages.ERROR,
                _("An error occurred while saving clearance levels.") + _("One of the OOI's doesn't exist"),
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
        scan_profiles = [EmptyScanProfile(reference=Reference.from_str(ooi)) for ooi in selected_oois]

        try:
            self.octopoes_api_connector.save_many_scan_profiles(scan_profiles, valid_time=datetime.now(timezone.utc))
        except (RequestException, RemoteException, ConnectionError):
            messages.add_message(
                request,
                messages.ERROR,
                _("An error occurred while setting clearance levels to inherit."),
            )
            return self.get(request, status=500, *args, **kwargs)
        except ObjectNotFoundException:
            messages.add_message(
                request,
                messages.ERROR,
                _("An error occurred while setting clearance levels to inherit: one of the OOIs doesn't exist."),
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

    def get_organization_indemnification(self):
        return Indemnification.objects.filter(organization=self.organization).exists()


class OOIListExportView(BaseOOIListView):
    def get(self, request, *args, **kwargs):
        file_type = request.GET.get("file_type")
        observed_at = self.get_observed_at()
        filters = self.get_active_filters()

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
