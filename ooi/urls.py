from django.urls import path

from ooi.views import (
    HostnameDetailView,
    HostnameListView,
    IPAddressDetailView,
    IPAddressListView,
    NetworkDetailView,
    NetworkListView,
)

app_name = "ooi"

urlpatterns = [
    path("network/", NetworkListView.as_view(), name="network-list"),
    path("network/<int:pk>/", NetworkDetailView.as_view(), name="network-detail"),
    path("ipaddress/", IPAddressListView.as_view(), name="ipaddress-list"),
    path("ipaddress/<int:pk>/", IPAddressDetailView.as_view(), name="ipaddress-detail"),
    path("hostname/", HostnameListView.as_view(), name="hostname-list"),
    path("hostname/<int:pk>/", HostnameDetailView.as_view(), name="hostname-detail"),
]
