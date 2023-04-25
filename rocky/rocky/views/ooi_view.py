from datetime import datetime, timezone
from time import sleep
from typing import List, Type
from uuid import uuid4

from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, TemplateView
from django.views.generic.edit import FormView
from django_otp.decorators import otp_required
from pydantic import ValidationError
from tools.forms.base import BaseRockyForm, ObservedAtForm
from tools.forms.settings import CLEARANCE_TYPE_CHOICES
from tools.models import SCAN_LEVEL
from tools.ooi_form import ClearanceFilterForm, OOIForm
from tools.view_helpers import Breadcrumb, BreadcrumbsMixin, get_mandatory_fields, get_ooi_url
from two_factor.views.utils import class_view_decorator

from octopoes.api.models import Declaration
from octopoes.models import DEFAULT_SCAN_LEVEL_FILTER, DEFAULT_SCAN_PROFILE_TYPE_FILTER, OOI, ScanLevel, ScanProfileType
from octopoes.models.ooi.findings import Finding, FindingType
from octopoes.models.types import get_collapsed_types
from rocky.bytes_client import BytesClient, get_bytes_client
from rocky.views.mixins import (
    ConnectorFormMixin,
    MultipleOOIMixin,
    SingleOOIMixin,
    SingleOOITreeMixin,
)


@class_view_decorator(otp_required)
class BaseOOIListView(MultipleOOIMixin, ConnectorFormMixin, ListView):
    connector_form_class = ObservedAtForm
    paginate_by = 150
    context_object_name = "ooi_list"
    ooi_types = get_collapsed_types().difference({Finding, FindingType})

    def get_queryset(self):
        scan_levels = DEFAULT_SCAN_LEVEL_FILTER
        selected_clearance_level = self.request.GET.getlist("clearance_level")
        if selected_clearance_level is not None:
            scan_levels = {ScanLevel(int(s)) for s in selected_clearance_level}

        scan_profile_types = DEFAULT_SCAN_PROFILE_TYPE_FILTER
        selected_clearance_type = self.request.GET.getlist("clearance_type")
        if selected_clearance_type is not None:
            scan_profile_types = {ScanProfileType(s) for s in selected_clearance_type}

        return self.get_list(self.get_observed_at(), scan_level=scan_levels, scan_profile_type=scan_profile_types)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["mandatory_fields"] = get_mandatory_fields(self.request)
        context["observed_at_form"] = self.get_connector_form()
        context["observed_at"] = self.get_observed_at()
        context["total_oois"] = len(self.object_list)

        selected_clearance_levels = self.request.GET.getlist("clearance_level")
        if not selected_clearance_levels:
            selected_clearance_levels = [choice for choice, _ in SCAN_LEVEL.choices]
        selected_clearance_types = self.request.GET.getlist("clearance_type")
        if not selected_clearance_types:
            selected_clearance_types = [choice for choice, _ in CLEARANCE_TYPE_CHOICES]

        context["clearance_level_filter_form"] = ClearanceFilterForm(
            selected_clearance_levels, selected_clearance_types
        )

        return context


@class_view_decorator(otp_required)
class BaseOOIDetailView(SingleOOITreeMixin, BreadcrumbsMixin, ConnectorFormMixin, TemplateView):
    def get(self, request, *args, **kwargs):
        self.ooi = self.get_ooi()
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["ooi"] = self.ooi
        context["mandatory_fields"] = get_mandatory_fields(self.request)
        context["observed_at"] = self.get_observed_at()

        return context

    def build_breadcrumbs(self) -> List[Breadcrumb]:
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


@class_view_decorator(otp_required)
class BaseOOIFormView(SingleOOIMixin, FormView):
    ooi_class: Type[OOI] = None
    form_class = OOIForm

    def get_ooi_class(self):
        return self.ooi.__class__ if hasattr(self, "ooi") else None

    def get_form(self, form_class=None) -> BaseRockyForm:
        if form_class is None:
            form_class = self.get_form_class()

        kwargs = self.get_form_kwargs()
        form = form_class(**kwargs)

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

    def save_ooi(self, data) -> OOI:
        new_ooi = self.ooi_class.parse_obj(data)

        task_id = uuid4()
        declaration = Declaration(ooi=new_ooi, valid_time=datetime.now(timezone.utc), task_id=str(task_id))

        get_bytes_client(self.organization.code).add_manual_proof(
            task_id, BytesClient.raw_from_declarations([declaration])
        )

        self.octopoes_api_connector.save_declaration(declaration)
        return new_ooi

    def form_valid(self, form):
        # Transform into OOI
        try:
            new_ooi = self.save_ooi(form.cleaned_data)
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

    def get_readonly_fields(self) -> List:
        if not hasattr(self, "ooi"):
            return []

        return self.ooi._natural_key_attrs
