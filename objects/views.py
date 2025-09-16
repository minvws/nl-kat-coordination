import datetime
from datetime import timezone
from enum import Enum

import django_filters
from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DeleteView, DetailView, ListView
from django_filters.views import FilterView

from objects.models import ObjectSet
from openkat.models import Organization
from openkat.permissions import KATModelPermissionRequiredMixin


class PageActions(Enum):
    DELETE = "delete"
    UPDATE_SCAN_PROFILE = "update-scan-profile"


class ObjectListView(ListView):
    template_name = "object_list.html"
    paginate_by = settings.VIEW_DEFAULT_PAGE_SIZE

    def get(self, request, *args, **kwargs):
        # TODO
        return redirect(reverse("ooi_list", kwargs={"organization_code": Organization.objects.first().code}))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"url": reverse("object_list"), "text": _("Objects")}]

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

        if obj.object_query:
            # TODO: fix
            # try:
            #     query = Query.from_path(obj.object_query)
            # except (ValueError, TypeNotFound):
            #     raise ValueError(f"Invalid query: {obj.object_query}")
            #
            # pk = Aliased(query.result_type, field="primary_key")
            # objects = connector.octopoes.ooi_repository.query(
            #     query.find(pk).where(query.result_type, primary_key=pk).limit(10), now,
            # )
            #
            # context["preview"] = [obj[1] for obj in objects]
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


class ObjectSetDeleteView(KATModelPermissionRequiredMixin, DeleteView):
    model = ObjectSet

    def form_invalid(self, form):
        return redirect(reverse("object_set_list"))

    def get_success_url(self, **kwargs):
        redirect_url = self.get_form().data.get("current_url")

        if redirect_url and url_has_allowed_host_and_scheme(redirect_url, allowed_hosts=None):
            return redirect_url

        return reverse_lazy("object_set_list")
