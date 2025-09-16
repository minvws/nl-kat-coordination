from django.urls import path

from oois.views import (
    HostnameDetailView,
    HostnameListView,
    IPAddressDetailView,
    IPAddressListView,
    NetworkDetailView,
    NetworkListView,
)

urlpatterns = [
    path("ooi/network/", NetworkListView.as_view(), name="network_list"),
    path("ooi/network/<int:pk>/", NetworkDetailView.as_view(), name="network_detail"),
    path("ooi/ipaddress/", IPAddressListView.as_view(), name="ipaddress_list"),
    path("ooi/ipaddress/<int:pk>/", IPAddressDetailView.as_view(), name="ipaddress_detail"),
    path("ooi/hostname/", HostnameListView.as_view(), name="hostname_list"),
    path("ooi/hostname/<int:pk>/", HostnameDetailView.as_view(), name="hostname_detail"),
]
