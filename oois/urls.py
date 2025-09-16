from django.urls import path

from oois.views import (
    HostnameDetailView,
    HostnameListView,
    IPAddressDetailView,
    IPAddressListView,
    NetworkDetailView,
    NetworkListView,
)

app_name = "oois"

urlpatterns = [
    path("ooi/network/", NetworkListView.as_view(), name="network-list"),
    path("ooi/network/<int:pk>/", NetworkDetailView.as_view(), name="network-detail"),
    path("ooi/ipaddress/", IPAddressListView.as_view(), name="ipaddress-list"),
    path("ooi/ipaddress/<int:pk>/", IPAddressDetailView.as_view(), name="ipaddress-detail"),
    path("ooi/hostname/", HostnameListView.as_view(), name="hostname-list"),
    path("ooi/hostname/<int:pk>/", HostnameDetailView.as_view(), name="hostname-detail"),
]
