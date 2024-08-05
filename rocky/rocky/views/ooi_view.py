from datetime import datetime, timezone
from time import sleep

from django import forms
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView
from django.views.generic.edit import FormView
from pydantic import ValidationError
from tools.forms.base import BaseRockyForm, ObservedAtForm
from tools.forms.ooi_form import _EXCLUDED_OOI_TYPES, ClearanceFilterForm, OOIForm
from tools.ooi_helpers import create_ooi
from tools.view_helpers import Breadcrumb, BreadcrumbsMixin, get_mandatory_fields, get_ooi_url

from octopoes.config.settings import DEFAULT_SCAN_LEVEL_FILTER, DEFAULT_SCAN_PROFILE_TYPE_FILTER
from octopoes.models import OOI, ScanLevel, ScanProfileType
from octopoes.models.ooi.findings import Finding, FindingType
from octopoes.models.types import get_collapsed_types, type_by_name
from rocky.paginator import RockyPaginator
from rocky.views.mixins import ConnectorFormMixin, OctopoesView, OOIList, SingleOOIMixin, SingleOOITreeMixin


class OOIFilterView(ConnectorFormMixin, OctopoesView):
    """
    Shows filter options with different filter forms and handles filter requests for OOIs.
    """

    connector_form_class = ObservedAtForm
    ooi_types = get_collapsed_types().difference({Finding, FindingType})
    scan_levels = DEFAULT_SCAN_LEVEL_FILTER
    scan_profile_types = DEFAULT_SCAN_PROFILE_TYPE_FILTER

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.filtered_ooi_types = request.GET.getlist("ooi_type", [])
        self.clearance_levels = request.GET.getlist("clearance_level", [])
        self.clearance_types = request.GET.getlist("clearance_type", [])

    def get_active_filters(self) -> dict[str, str]:
        active_filters = {}
        if self.filtered_ooi_types:
            active_filters[_("OOI types: ")] = ", ".join(self.filtered_ooi_types)
        if self.clearance_levels:
            clearance_level = ["L" + str(cl) for cl in self.clearance_levels]
            active_filters[_("Clearance level: ")] = ", ".join(clearance_level)
        if self.clearance_types:
            active_filters[_("Clearance type: ")] = ", ".join(self.clearance_types)
        return active_filters

    def get_ooi_scan_levels(self) -> set[ScanLevel]:
        if not self.clearance_levels:
            return self.scan_levels
        return {ScanLevel(int(cl)) for cl in self.clearance_levels}

    def get_ooi_profile_types(self) -> set[ScanProfileType]:
        if not self.clearance_types:
            return self.scan_profile_types
        return {ScanProfileType(ct) for ct in self.clearance_types}

    def get_ooi_types(self) -> set[type[OOI]]:
        if not self.filtered_ooi_types:
            return self.ooi_types
        return {type_by_name(t) for t in self.filtered_ooi_types if t not in _EXCLUDED_OOI_TYPES}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["observed_at"] = self.observed_at
        context["observed_at_form"] = self.get_connector_form()

        context["ooi_types_selection"] = self.filtered_ooi_types

        context["clearance_levels_selection"] = self.clearance_levels
        context["clearance_level_filter_form"] = ClearanceFilterForm(self.request.GET)

        context["clearance_types_selection"] = self.clearance_types

        context["active_filters"] = self.get_active_filters()
        return context


class BaseOOIListView(OOIFilterView, ListView):
    paginate_by = 150
    context_object_name = "ooi_list"
    paginator = RockyPaginator

    def get_queryset(self) -> OOIList:
        return OOIList(
            self.octopoes_api_connector,
            ooi_types=self.get_ooi_types(),
            valid_time=self.observed_at,
            scan_level=self.get_ooi_scan_levels(),
            scan_profile_type=self.get_ooi_profile_types(),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["mandatory_fields"] = get_mandatory_fields(self.request)
        context["total_oois"] = len(self.object_list)
        return context


class BaseOOIDetailView(BreadcrumbsMixin, SingleOOITreeMixin, ConnectorFormMixin):
    connector_form_class = ObservedAtForm

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.ooi = self.get_ooi()

    def get_current_ooi(self) -> OOI | None:
        """
        Some OOIs have an old valid time, this will fetch the latest OOI for today.
        """
        now = datetime.now(timezone.utc)
        if self.observed_at.date() == now.date():
            return self.ooi
        try:
            return self.get_ooi(pk=self.get_ooi_id(), observed_at=now)
        except Http404:
            return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["ooi"] = self.ooi
        context["ooi_current"] = self.get_current_ooi()
        context["mandatory_fields"] = get_mandatory_fields(self.request)
        context["observed_at"] = self.observed_at
        context["observed_at_form"] = self.get_connector_form()

        return context

    def build_breadcrumbs(self) -> list[Breadcrumb]:
        start: Breadcrumb
        if isinstance(self.ooi, Finding):
            start = {
                "url": reverse("finding_list", kwargs={"organization_code": self.organization.code}),
                "text": _("Findings"),
            }
        else:
            start = {
                "url": reverse("ooi_list", kwargs={"organization_code": self.organization.code}),
                "text": _("Objects"),
            }
        return [
            start,
            {
                "url": get_ooi_url("ooi_detail", self.ooi.primary_key, self.organization.code),
                "text": self.ooi.human_readable,
            },
        ]


class BaseOOIFormView(SingleOOIMixin, FormView):
    ooi_class: type[OOI]
    form_class: forms.Form = OOIForm

    def get_ooi_class(self):
        return self.ooi.__class__ if hasattr(self, "ooi") else None

    def get_form(self, form_class=None) -> BaseRockyForm:
        form = super().get_form(form_class)

        # Disable natural key attributes
        if self.get_readonly_fields():
            for readonly_field in self.get_readonly_fields():
                form.fields[readonly_field].disabled = True

        return form

    def get_form_kwargs(self):
        kwargs = {
            "ooi_class": self.get_ooi_class(),
            "connector": self.octopoes_api_connector,
        }
        kwargs.update(super().get_form_kwargs())

        return kwargs

    def form_valid(self, form):
        # Transform into OOI
        try:
            new_ooi = self.ooi_class.parse_obj(form.cleaned_data)
            create_ooi(
                self.octopoes_api_connector,
                self.bytes_client,
                new_ooi,
                datetime.now(timezone.utc),
            )
            sleep(1)
            return redirect(self.get_ooi_success_url(new_ooi))
        except ValidationError as exception:
            for error in exception.errors():
                form.add_error(error["loc"][0], error["msg"])
            return self.form_invalid(form)
        except Exception as exception:
            form.add_error("__all__", str(exception))
            return self.form_invalid(form)

    def get_ooi_success_url(self, ooi: OOI) -> str:
        return get_ooi_url("ooi_detail", ooi.primary_key, self.organization.code)

    def get_readonly_fields(self) -> list:
        if not hasattr(self, "ooi"):
            return []

        return self.ooi._natural_key_attrs
