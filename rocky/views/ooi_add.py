import logging
from typing import Type

from django.http import Http404
from django.shortcuts import redirect
from django.urls.base import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from django_otp.decorators import otp_required
from octopoes.models import OOI
from octopoes.models.types import type_by_name
from two_factor.views.utils import class_view_decorator

from rocky.views import BaseOOIFormView
from tools.ooi_helpers import OOI_TYPES_WITHOUT_FINDINGS
from tools.view_helpers import existing_ooi_type

logger = logging.getLogger(__name__)


def ooi_type_input_choices():
    ooi_types = OOI_TYPES_WITHOUT_FINDINGS
    ooi_types.sort()
    return [{"value": ooi_type, "text": ooi_type} for ooi_type in ooi_types]


@class_view_decorator(otp_required)
class OOIAddTypeSelectView(TemplateView):
    template_name = "oois/ooi_add_type_select.html"

    def get(self, request, *args, **kwargs):
        if "add_ooi_type" in request.GET and existing_ooi_type(request.GET["add_ooi_type"]):
            return redirect(reverse("ooi_add", kwargs={"ooi_type": request.GET["add_ooi_type"]}))

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["ooi_types"] = ooi_type_input_choices()
        context["breadcrumbs"] = [
            {"url": reverse("ooi_list"), "text": _("Objects")},
            {"url": reverse("ooi_add_type_select"), "text": _("Add object")},
        ]

        return context


@class_view_decorator(otp_required)
class OOIAddView(BaseOOIFormView):
    template_name = "oois/ooi_add.html"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.ooi_class = self.get_ooi_class()
        self.initial = request.GET

    def get_ooi_class(self) -> Type[OOI]:
        try:
            return type_by_name(self.kwargs["ooi_type"])
        except KeyError:
            raise Http404("OOI not found")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["type"] = self.ooi_class.get_ooi_type()
        context["breadcrumbs"] = [
            {"url": reverse("ooi_list"), "text": _("Objects")},
            {"url": reverse("ooi_add_type_select"), "text": _("Type select")},
            {
                "url": reverse("ooi_add", kwargs={"ooi_type": self.ooi_class.get_ooi_type()}),
                "text": _("Add %(ooi_type)s") % {"ooi_type": self.ooi_class.get_ooi_type()},
            },
        ]

        return context
