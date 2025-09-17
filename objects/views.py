from typing import TYPE_CHECKING

from django.conf import settings
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, ListView

from objects.models import Hostname, IPAddress, Network

if TYPE_CHECKING:
    from django.db.models.query import QuerySet


class NetworkListView(ListView):
    model = Network
    template_name = "objects/network_list.html"
    context_object_name = "networks"
    paginate_by = settings.VIEW_DEFAULT_PAGE_SIZE

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


class IPAddressListView(ListView):
    model = IPAddress
    template_name = "objects/ipaddress_list.html"
    context_object_name = "ipaddresses"
    paginate_by = settings.VIEW_DEFAULT_PAGE_SIZE

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


class HostnameListView(ListView):
    model = Hostname
    template_name = "objects/hostname_list.html"
    context_object_name = "hostnames"
    paginate_by = settings.VIEW_DEFAULT_PAGE_SIZE

    def get_queryset(self) -> "QuerySet[Hostname]":
        return Hostname.objects.select_related("network")

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
