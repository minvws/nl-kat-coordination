from typing import TYPE_CHECKING

from django.views.generic import DetailView, ListView

from ooi.models import Hostname, IPAddress, Network

if TYPE_CHECKING:
    from django.db.models.query import QuerySet


class NetworkListView(ListView[Network]):
    model = Network
    template_name = "ooi/network_list.html"
    context_object_name = "networks"
    paginate_by = 100


class NetworkDetailView(DetailView[Network]):
    model = Network
    template_name = "ooi/network_detail.html"
    context_object_name = "network"


class IPAddressListView(ListView[IPAddress]):
    model = IPAddress
    template_name = "ooi/ipaddress_list.html"
    context_object_name = "ipaddresses"
    paginate_by = 100

    def get_queryset(self) -> "QuerySet[IPAddress]":
        return IPAddress.objects.select_related("network")


class IPAddressDetailView(DetailView[IPAddress]):
    model = IPAddress
    template_name = "ooi/ipaddress_detail.html"
    context_object_name = "ipaddress"

    def get_queryset(self) -> "QuerySet[IPAddress]":
        return IPAddress.objects.select_related("network").prefetch_related("ipport_set")


class HostnameListView(ListView[Hostname]):
    model = Hostname
    template_name = "ooi/hostname_list.html"
    context_object_name = "hostnames"
    paginate_by = 100

    def get_queryset(self) -> "QuerySet[Hostname]":
        return Hostname.objects.select_related("network")


class HostnameDetailView(DetailView[Hostname]):
    model = Hostname
    template_name = "ooi/hostname_detail.html"
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
