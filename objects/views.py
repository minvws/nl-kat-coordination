import datetime
from datetime import timezone
from enum import Enum

import django_filters
from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DetailView, ListView
from django_filters.views import FilterView

from objects.models import ObjectSet
from octopoes.models.exception import TypeNotFound
from octopoes.models.ooi.findings import Finding, FindingType
from octopoes.models.ooi.reports import AssetReport, BaseReport, HydratedReport, Report, ReportData, ReportRecipe
from octopoes.models.types import get_collapsed_types
from octopoes.xtdb.query import Aliased, Query
from openkat.enums import CUSTOM_SCAN_LEVEL
from openkat.forms.ooi_form import _EXCLUDED_OOI_TYPES, OOISearchForm, OOITypeMultiCheckboxForm
from openkat.models import Organization
from openkat.permissions import KATModelPermissionRequiredMixin
from openkat.view_helpers import get_mandatory_fields
from openkat.views.mixins import OOIList


class PageActions(Enum):
    DELETE = "delete"
    UPDATE_SCAN_PROFILE = "update-scan-profile"


class ObjectListView(ListView):
    template_name = "object_list.html"
    paginate_by = settings.VIEW_DEFAULT_PAGE_SIZE

    def get(self, request, *args, **kwargs):
        # TODO
        return redirect(reverse("ooi_list", kwargs={"organization_code": Organization.objects.first().code}))

    def get_queryset(self):
        # TODO: handle
        organization = Organization.objects.first()

        return OOIList(settings.OCTOPOES_FACTORY(organization.code), **self.get_queryset_params())

    def get_queryset_params(self):
        return {
            "valid_time": datetime.datetime.now(timezone.utc),
            "ooi_types": {
                t
                for t in get_collapsed_types().difference(
                    {Finding, FindingType, BaseReport, Report, ReportRecipe, AssetReport, ReportData, HydratedReport}
                )
                if t not in _EXCLUDED_OOI_TYPES
            },
            "scan_level": settings.DEFAULT_SCAN_LEVEL_FILTER,
            "scan_profile_type": settings.DEFAULT_SCAN_PROFILE_TYPE_FILTER,
            "search_string": "",
            "order_by": "scan_level" if self.request.GET.get("order_by", "") == "scan_level" else "object_type",
            "asc_desc": "desc" if self.request.GET.get("sorting_order", "") == "desc" else "asc",
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"url": reverse("object_list"), "text": _("Objects")}]

        context["ooi_type_form"] = OOITypeMultiCheckboxForm(self.request.GET)
        context["ooi_search_form"] = OOISearchForm(self.request.GET)
        context["mandatory_fields"] = get_mandatory_fields(self.request, params=["observed_at"])
        context["member"] = self.request.user
        context["scan_levels"] = [alias for _, alias in CUSTOM_SCAN_LEVEL.choices]

        # TODO: handle
        context["organization"] = Organization.objects.first()
        context["may_update_clearance_level"] = True

        return context


class ObjectSetFilter(django_filters.FilterSet):
    object_query = django_filters.CharFilter(label="Object Query", lookup_expr="icontains")
    name = django_filters.CharFilter(label="Name", lookup_expr="icontains")
    description = django_filters.CharFilter(label="Description", lookup_expr="icontains")

    class Meta:
        model = ObjectSet
        fields = ["name", "description", "object_query"]


class ObjectSetListView(FilterView):
    template_name = "object_set_list.html"
    model = ObjectSet
    paginate_by = settings.VIEW_DEFAULT_PAGE_SIZE
    filterset_class = ObjectSetFilter

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"url": reverse("object_list"), "text": _("Objects")}]

        return context


class ObjectSetDetailView(DetailView):
    template_name = "object_set.html"
    model = ObjectSet

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {"url": reverse("object_list"), "text": _("Objects")},
            {"url": reverse("object_set_detail", kwargs={"pk": self.get_object().id}), "text": _("Object Set Detail")},

        ]

        now = datetime.datetime.now(timezone.utc)
        obj = self.get_object()

        # TODO: handle...
        org = Organization.objects.first()
        connector = settings.OCTOPOES_FACTORY(org.code)

        if obj.object_query:
            try:
                query = Query.from_path(obj.object_query)
            except (ValueError, TypeNotFound):
                raise ValueError(f"Invalid query: {obj.object_query}")

            pk = Aliased(query.result_type, field="primary_key")
            objects = connector.octopoes.ooi_repository.query(
                query.find(pk).where(query.result_type, primary_key=pk).limit(10), now,
            )

            context["preview"] = [obj[1] for obj in objects]
            context["preview_organization"] = org
        else:
            context["preview"] = None
            context["preview_organization"] = None

        return context


class ObjectSetCreateView(KATModelPermissionRequiredMixin, CreateView):
    model = ObjectSet
    fields = ["name", "all_objects", "object_query", "description", "dynamic"]
    template_name = "object_set_form.html"

    def get_success_url(self, **kwargs):
        redirect_url = self.get_form().data.get("current_url")

        if redirect_url and url_has_allowed_host_and_scheme(redirect_url, allowed_hosts=None):
            return redirect_url

        return reverse_lazy("object_set_list")
