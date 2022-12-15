from datetime import datetime, timezone
from time import sleep
from typing import Type, List

from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.views.generic import TemplateView
from django.views.generic.edit import FormView
from django_otp.decorators import otp_required
from octopoes.api.models import Declaration
from octopoes.models import OOI
from pydantic import ValidationError
from two_factor.views.utils import class_view_decorator

from rocky.views.mixins import (
    SingleOOIMixin,
    SingleOOITreeMixin,
    OctopoesAPIImproperlyConfigured,
    MultipleOOIMixin,
    ConnectorFormMixin,
)
from tools.forms import BaseRockyForm, ObservedAtForm
from tools.ooi_form import OOIForm
from tools.view_helpers import get_ooi_url, get_mandatory_fields


@class_view_decorator(otp_required)
class BaseOOIListView(MultipleOOIMixin, ConnectorFormMixin, TemplateView):
    connector_form_class = ObservedAtForm
    oois_per_page = 150

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        observed_at = self.get_observed_at()
        page_number = self.request.GET.get("page")
        oois = self.get_list(observed_at)
        paginator = Paginator(oois, self.oois_per_page)

        try:
            page_obj = paginator.get_page(page_number)
        except EmptyPage:
            page_obj = paginator.get_page(1)

        context["mandatory_fields"] = get_mandatory_fields(self.request)
        context["observed_at_form"] = self.get_connector_form()
        context["observed_at"] = observed_at
        context["total_oois"] = oois.count
        try:
            context["ooi_list"] = page_obj
        except OctopoesAPIImproperlyConfigured as e:
            context["ooi_list"] = []
            messages.add_message(self.request, messages.ERROR, str(e))

        return context


@class_view_decorator(otp_required)
class BaseOOIDetailView(SingleOOITreeMixin, ConnectorFormMixin, TemplateView):
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.api_connector = self.get_api_connector()

    def get(self, request, *args, **kwargs):
        self.ooi = self.get_ooi()
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["ooi"] = self.ooi
        context["mandatory_fields"] = get_mandatory_fields(self.request)
        context["observed_at"] = self.get_observed_at()

        return context


@class_view_decorator(otp_required)
class BaseOOIFormView(SingleOOIMixin, FormView):
    ooi_class: Type[OOI] = None
    form_class = OOIForm

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.api_connector = self.get_api_connector()

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
            "connector": self.get_api_connector(),
        }
        kwargs.update(super().get_form_kwargs())

        return kwargs

    def save_ooi(self, data) -> OOI:
        api_connector = self.get_api_connector()
        new_ooi = self.ooi_class.parse_obj(data)
        api_connector.save_declaration(Declaration(ooi=new_ooi, valid_time=datetime.now(timezone.utc)))
        return new_ooi

    def form_valid(self, form):
        # Transform into OOI
        try:
            new_ooi = self.save_ooi(form.cleaned_data)
            sleep(1)
            return redirect(self.get_success_url(new_ooi))
        except ValidationError as exception:
            for error in exception.errors():
                form.add_error(error["loc"][0], error["msg"])
            return self.form_invalid(form)
        except Exception as exception:
            form.add_error("__all__", str(exception))
            return self.form_invalid(form)

    def get_success_url(self, ooi) -> str:
        return get_ooi_url("ooi_detail", ooi.primary_key)

    def get_readonly_fields(self) -> List:
        if not hasattr(self, "ooi"):
            return []

        return self.ooi._natural_key_attrs


@class_view_decorator(otp_required)
class BaseDeleteOOIView(SingleOOIMixin, TemplateView):
    success_url = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.api_connector = self.get_api_connector()

    def delete(self, request):
        self.api_connector.delete(self.ooi.reference)

        return HttpResponseRedirect(self.success_url)

    # Add support for browsers which only accept GET and POST for now.
    def post(self, request):
        return self.delete(request)
