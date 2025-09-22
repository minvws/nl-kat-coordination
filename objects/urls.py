from django.urls import path
from rest_framework import routers

from objects.views import (
    FindingCreateView,
    FindingDeleteView,
    FindingListView,
    HostnameCreateView,
    HostnameDeleteView,
    HostnameDetailView,
    HostnameListView,
    IPAddressCreateView,
    IPAddressDeleteView,
    IPAddressDetailView,
    IPAddressListView,
    NetworkCreateView,
    NetworkDeleteView,
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
    FindingTypeViewSet,
    FindingViewSet,
    HostnameViewSet,
    IPAddressViewSet,
    IPPortViewSet,
    NetworkViewSet,
    ObjectViewSet,
)

app_name = "objects"

object_router = routers.SimpleRouter()
object_router.register(r"", ObjectViewSet, basename="object")
object_router.register(r"findingtype", FindingTypeViewSet, basename="findingtype")
object_router.register(r"finding", FindingViewSet, basename="finding")
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
    path("objects/finding/", FindingListView.as_view(), name="finding_list"),
    path("objects/finding/add/", FindingCreateView.as_view(), name="add_finding"),
    path("objects/finding/<int:pk>/delete/", FindingDeleteView.as_view(), name="delete_finding"),
    path("objects/network/", NetworkListView.as_view(), name="network_list"),
    path("objects/network/<int:pk>/", NetworkDetailView.as_view(), name="network_detail"),
    path("objects/network/add/", NetworkCreateView.as_view(), name="add_network"),
    path("objects/network/<int:pk>/delete/", NetworkDeleteView.as_view(), name="delete_network"),
    path("objects/ipaddress/", IPAddressListView.as_view(), name="ipaddress_list"),
    path("objects/ipaddress/<int:pk>/", IPAddressDetailView.as_view(), name="ipaddress_detail"),
    path("objects/ipaddress/add/", IPAddressCreateView.as_view(), name="add_ipaddress"),
    path("objects/ipaddress/<int:pk>/delete/", IPAddressDeleteView.as_view(), name="delete_ipaddress"),
    path("objects/hostname/", HostnameListView.as_view(), name="hostname_list"),
    path("objects/hostname/<int:pk>/", HostnameDetailView.as_view(), name="hostname_detail"),
    path("objects/hostname/add/", HostnameCreateView.as_view(), name="add_hostname"),
    path("objects/hostname/<int:pk>/delete/", HostnameDeleteView.as_view(), name="delete_hostname"),
]
