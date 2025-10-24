from django.urls import path
from rest_framework import routers

from objects.views import (
    DNSAAAARecordDeleteView,
    DNSARecordDeleteView,
    DNSCAARecordDeleteView,
    DNSCNAMERecordDeleteView,
    DNSMXRecordDeleteView,
    DNSNSRecordDeleteView,
    DNSPTRRecordDeleteView,
    DNSSRVRecordDeleteView,
    DNSTXTRecordDeleteView,
    FindingCreateView,
    FindingDeleteView,
    FindingListView,
    GenericAssetCreateView,
    GenericAssetCSVUploadView,
    HostnameCreateView,
    HostnameCSVUploadView,
    HostnameDeleteView,
    HostnameDetailView,
    HostnameListView,
    HostnameScanLevelDetailView,
    HostnameScanLevelUpdateView,
    HostnameTasksDetailView,
    IPAddressCreateView,
    IPAddressCSVUploadView,
    IPAddressDeleteView,
    IPAddressDetailView,
    IPAddressListView,
    IPAddressScanLevelDetailView,
    IPAddressScanLevelUpdateView,
    IPAddressTasksDetailView,
    IPPortDeleteView,
    IPPortSoftwareDeleteView,
    NetworkCreateView,
    NetworkDeleteView,
    NetworkDetailView,
    NetworkListView,
    NetworkScanLevelDetailView,
    NetworkScanLevelUpdateView,
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
    SoftwareViewSet,
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
object_router.register(r"software", SoftwareViewSet, basename="software")

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
    # Generic asset creation
    path("objects/assets/add/", GenericAssetCreateView.as_view(), name="generic_asset_create"),
    path("objects/assets/upload-csv/", GenericAssetCSVUploadView.as_view(), name="generic_asset_csv_upload"),
    path("objects/network/", NetworkListView.as_view(), name="network_list"),
    path("objects/network/add/", NetworkCreateView.as_view(), name="add_network"),
    path("objects/network/<int:pk>/", NetworkDetailView.as_view(), name="network_detail"),
    path(
        "objects/network/<int:pk>/scan-level/", NetworkScanLevelDetailView.as_view(), name="network_scan_level_detail"
    ),
    path("objects/network/<int:pk>/delete/", NetworkDeleteView.as_view(), name="delete_network"),
    path(
        "objects/network/<int:pk>/update-scan-level/",
        NetworkScanLevelUpdateView.as_view(),
        name="update_network_scan_level",
    ),
    path("objects/ipaddress/", IPAddressListView.as_view(), name="ipaddress_list"),
    path("objects/ipaddress/add/", IPAddressCreateView.as_view(), name="add_ipaddress"),
    path("objects/ipaddress/upload-csv/", IPAddressCSVUploadView.as_view(), name="ipaddress_csv_upload"),
    path("objects/ipaddress/<int:pk>/", IPAddressDetailView.as_view(), name="ipaddress_detail"),
    path("objects/ipaddress/<int:pk>/delete/", IPAddressDeleteView.as_view(), name="delete_ipaddress"),
    path(
        "objects/ipaddress/<int:pk>/scan-level/",
        IPAddressScanLevelDetailView.as_view(),
        name="ipaddress_scan_level_detail",
    ),
    path(
        "objects/ipaddress/<int:pk>/update-scan-level/",
        IPAddressScanLevelUpdateView.as_view(),
        name="update_ipaddress_scan_level",
    ),
    path("objects/ipaddress/<int:pk>/tasks/", IPAddressTasksDetailView.as_view(), name="ipaddress_tasks_detail"),
    path("objects/hostname/", HostnameListView.as_view(), name="hostname_list"),
    path("objects/hostname/add/", HostnameCreateView.as_view(), name="add_hostname"),
    path("objects/hostname/upload-csv/", HostnameCSVUploadView.as_view(), name="hostname_csv_upload"),
    path("objects/hostname/<int:pk>/", HostnameDetailView.as_view(), name="hostname_detail"),
    path("objects/hostname/<int:pk>/delete/", HostnameDeleteView.as_view(), name="delete_hostname"),
    path(
        "objects/hostname/<int:pk>/scan-level/",
        HostnameScanLevelDetailView.as_view(),
        name="hostname_scan_level_detail",
    ),
    path(
        "objects/hostname/<int:pk>/update-scan-level/",
        HostnameScanLevelUpdateView.as_view(),
        name="update_hostname_scan_level",
    ),
    path("objects/hostname/<int:pk>/tasks/", HostnameTasksDetailView.as_view(), name="hostname_tasks_detail"),
    # DNS Record delete views
    path("objects/dnsarecord/<int:pk>/delete/", DNSARecordDeleteView.as_view(), name="delete_dnsarecord"),
    path("objects/dnsaaaarecord/<int:pk>/delete/", DNSAAAARecordDeleteView.as_view(), name="delete_dnsaaaarecord"),
    path("objects/dnsptrrecord/<int:pk>/delete/", DNSPTRRecordDeleteView.as_view(), name="delete_dnsptrrecord"),
    path("objects/dnscnamerecord/<int:pk>/delete/", DNSCNAMERecordDeleteView.as_view(), name="delete_dnscnamerecord"),
    path("objects/dnsmxrecord/<int:pk>/delete/", DNSMXRecordDeleteView.as_view(), name="delete_dnsmxrecord"),
    path("objects/dnsnsrecord/<int:pk>/delete/", DNSNSRecordDeleteView.as_view(), name="delete_dnsnsrecord"),
    path("objects/dnscaarecord/<int:pk>/delete/", DNSCAARecordDeleteView.as_view(), name="delete_dnscaarecord"),
    path("objects/dnstxtrecord/<int:pk>/delete/", DNSTXTRecordDeleteView.as_view(), name="delete_dnstxtrecord"),
    path("objects/dnssrvrecord/<int:pk>/delete/", DNSSRVRecordDeleteView.as_view(), name="delete_dnssrvrecord"),
    # IPPort and Software delete views
    path("objects/ipport/<int:pk>/delete/", IPPortDeleteView.as_view(), name="delete_ipport"),
    path(
        "objects/ipport/<int:port_pk>/software/<int:pk>/delete/",
        IPPortSoftwareDeleteView.as_view(),
        name="delete_ipport_software",
    ),
]
