from typing import TYPE_CHECKING

import django_filters
from django.conf import settings
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import OuterRef, QuerySet, Subquery
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DeleteView, DetailView
from django_filters.views import FilterView

from objects.models import Finding, Hostname, IPAddress, Network, ScanLevel
from openkat.permissions import KATModelPermissionRequiredMixin

if TYPE_CHECKING:
    from django.db.models.query import QuerySet


class NetworkFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(label="Name", lookup_expr="contains")

    class Meta:
        model = Network
        fields = ["name"]


class NetworkListView(FilterView):
    model = Network
    template_name = "objects/network_list.html"
    context_object_name = "networks"
    paginate_by = settings.VIEW_DEFAULT_PAGE_SIZE
    filterset_class = NetworkFilter

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"url": reverse("objects:network_list"), "text": _("Networks")}]

        return context


class NetworkDetailView(DetailView):
    model = Network
    template_name = "objects/network_detail.html"
    context_object_name = "network"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"url": reverse("objects:network_list"), "text": _("Networks")}]

        return context


class NetworkCreateView(KATModelPermissionRequiredMixin, CreateView):
    model = Network
    template_name = "objects/generic_object_form.html"
    fields = ["name"]
    success_url = reverse_lazy("objects:network_list")


class NetworkDeleteView(KATModelPermissionRequiredMixin, DeleteView):
    model = Network
    success_url = reverse_lazy("objects:network_list")

    def form_invalid(self, form):
        return redirect(reverse("objects:network_list"))


class FindingFilter(django_filters.FilterSet):
    finding_type__code = django_filters.CharFilter(label="Finding Type", lookup_expr="contains")

    class Meta:
        model = Finding
        fields = ["finding_type__code"]


class FindingListView(FilterView):
    model = Finding
    template_name = "objects/finding_list.html"
    context_object_name = "findings"
    paginate_by = settings.VIEW_DEFAULT_PAGE_SIZE
    filterset_class = FindingFilter

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"url": reverse("objects:finding_list"), "text": _("Findings")}]

        return context


class FindingCreateView(KATModelPermissionRequiredMixin, CreateView):
    model = Finding
    template_name = "objects/generic_object_form.html"
    fields = ["organization", "finding_type", "object_type", "object_id"]  # TODO: make easy
    success_url = reverse_lazy("objects:finding_list")


class FindingDeleteView(KATModelPermissionRequiredMixin, DeleteView):
    model = Finding
    success_url = reverse_lazy("objects:finding_list")

    def form_invalid(self, form):
        return redirect(reverse("objects:finding_list"))


class IPAddressFilter(django_filters.FilterSet):
    address = django_filters.CharFilter(label="Address", lookup_expr="contains")

    class Meta:
        model = IPAddress
        fields = ["address"]


class IPAddressListView(FilterView):
    model = IPAddress
    template_name = "objects/ipaddress_list.html"
    context_object_name = "ipaddresses"
    paginate_by = settings.VIEW_DEFAULT_PAGE_SIZE
    filterset_class = IPAddressFilter

    def get_queryset(self) -> "QuerySet[IPAddress]":
        return IPAddress.objects.select_related("network")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"url": reverse("objects:ipaddress_list"), "text": _("IPAddresses")}]

        return context


class IPAddressDetailView(DetailView):
    model = IPAddress
    template_name = "objects/ipaddress_detail.html"
    context_object_name = "ipaddress"

    def get_queryset(self) -> "QuerySet[IPAddress]":
        return IPAddress.objects.select_related("network").prefetch_related("ipport_set")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"url": reverse("objects:ipaddress_list"), "text": _("IPAddresses")}]

        return context


class IPAddressCreateView(KATModelPermissionRequiredMixin, CreateView):
    model = IPAddress
    template_name = "objects/generic_object_form.html"
    fields = ["network", "address"]
    success_url = reverse_lazy("objects:ipaddress_list")


class IPAddressDeleteView(KATModelPermissionRequiredMixin, DeleteView):
    model = IPAddress
    success_url = reverse_lazy("objects:ipaddress_list")

    def form_invalid(self, form):
        return redirect(reverse("objects:ipaddress_list"))


class HostnameFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(label="Name", lookup_expr="contains")

    class Meta:
        model = Hostname
        fields = ["name"]


class HostnameListView(FilterView):
    model = Hostname
    template_name = "objects/hostname_list.html"
    context_object_name = "hostnames"
    paginate_by = settings.VIEW_DEFAULT_PAGE_SIZE
    filterset_class = HostnameFilter

    def get_queryset(self) -> "QuerySet[Hostname]":
        scan_level_query = (
            ScanLevel.objects.filter(object_type="hostname", object_id=OuterRef("id"))
            .values("object_id")
            .order_by()
            .annotate(scan_levels=ArrayAgg("scan_level"))  # collect scan levels in subquery
            .annotate(organizations=ArrayAgg("organization"))  # collect scan levels in subquery
        )

        return (
            Hostname.objects.select_related("network")
            .annotate(scan_levels=Subquery(scan_level_query.values("scan_levels")))
            .annotate(organizations=Subquery(scan_level_query.values("organizations")))
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"url": reverse("objects:hostname_list"), "text": _("Hostnames")}]

        return context


class HostnameDetailView(DetailView):
    model = Hostname
    template_name = "objects/hostname_detail.html"
    context_object_name = "hostname"

    def get_queryset(self) -> "QuerySet[Hostname]":
        return Hostname.objects.select_related("network").prefetch_related(
            "dnsarecord_set",
            "dnsaaaarecord_set",
            "dnsptrrecord_set",
            "cname_records",
            "cname_targets",
            "mx_records",
            "mx_targets",
            "ns_records",
            "ns_targets",
            "dnscaarecord_set",
            "dnstxtrecord_set",
            "dnssrvrecord_set",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"url": reverse("objects:hostname_list"), "text": _("Hostnames")}]

        return context


class HostnameDeleteView(KATModelPermissionRequiredMixin, DeleteView):
    model = Hostname
    success_url = reverse_lazy("objects:hostname_list")

    def form_invalid(self, form):
        return redirect(reverse("objects:hostname_list"))


class HostnameCreateView(KATModelPermissionRequiredMixin, CreateView):
    model = Hostname
    template_name = "objects/generic_object_form.html"
    fields = ["network", "name"]
    success_url = reverse_lazy("objects:hostname_list")
