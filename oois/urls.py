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
    path("oois/network/", NetworkListView.as_view(), name="network_list"),
    path("oois/network/<int:pk>/", NetworkDetailView.as_view(), name="network_detail"),
    path("oois/ipaddress/", IPAddressListView.as_view(), name="ipaddress_list"),
    path("oois/ipaddress/<int:pk>/", IPAddressDetailView.as_view(), name="ipaddress_detail"),
    path("oois/hostname/", HostnameListView.as_view(), name="hostname_list"),
    path("oois/hostname/<int:pk>/", HostnameDetailView.as_view(), name="hostname_detail"),
]
