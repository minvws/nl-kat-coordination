from django.urls import path
from rest_framework import routers

from objects.views import (
    HostnameDetailView,
    HostnameListView,
    IPAddressDetailView,
    IPAddressListView,
    NetworkDetailView,
    NetworkListView,
)
from objects.viewsets import (
    DNSAAAARecordViewSet,
    DNSARecordViewSet,
    DNSCAARecordViewSet,
    DNSCNAMERecordViewSet,
    DNSMXRecordViewSet,
    DNSNSRecordViewSet,
    DNSPTRRecordViewSet,
    DNSSRVRecordViewSet,
    DNSTXTRecordViewSet,
    HostnameViewSet,
    IPAddressViewSet,
    IPPortViewSet,
    NetworkViewSet,
)

app_name = "objects"

object_router = routers.SimpleRouter()
object_router.register(r"network", NetworkViewSet, basename="network")
object_router.register(r"hostname", HostnameViewSet, basename="hostname")
object_router.register(r"ipaddress", IPAddressViewSet, basename="ipaddress")
object_router.register(r"ipport", IPPortViewSet, basename="ipport")
object_router.register(r"dnsarecord", DNSARecordViewSet, basename="dnsarecord")
object_router.register(r"dnsaaaarecord", DNSAAAARecordViewSet, basename="dnsaaaarecord")
object_router.register(r"dnsptrrecord", DNSPTRRecordViewSet, basename="dnsptrrecord")
object_router.register(r"dnscnamerecord", DNSCNAMERecordViewSet, basename="dnscnamerecord")
object_router.register(r"dnsmxrecord", DNSMXRecordViewSet, basename="dnsmxrecord")
object_router.register(r"dnsnsrecord", DNSNSRecordViewSet, basename="dnsnsrecord")
object_router.register(r"dnscaarecord", DNSCAARecordViewSet, basename="dnscaarecord")
object_router.register(r"dnstxtrecord", DNSTXTRecordViewSet, basename="dnstxtrecord")
object_router.register(r"dnssrvrecord", DNSSRVRecordViewSet, basename="dnssrvrecord")


urlpatterns = [
    path("objects/network/", NetworkListView.as_view(), name="network_list"),
    path("objects/network/<int:pk>/", NetworkDetailView.as_view(), name="network_detail"),
    path("objects/ipaddress/", IPAddressListView.as_view(), name="ipaddress_list"),
    path("objects/ipaddress/<int:pk>/", IPAddressDetailView.as_view(), name="ipaddress_detail"),
    path("objects/hostname/", HostnameListView.as_view(), name="hostname_list"),
    path("objects/hostname/<int:pk>/", HostnameDetailView.as_view(), name="hostname_detail"),
]
