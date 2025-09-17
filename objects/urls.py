from django.urls import path

from objects.views import (
    HostnameDetailView,
    HostnameListView,
    IPAddressDetailView,
    IPAddressListView,
    NetworkDetailView,
    NetworkListView,
)

app_name = "objects"

urlpatterns = [
    path("objects/network/", NetworkListView.as_view(), name="network_list"),
    path("objects/network/<int:pk>/", NetworkDetailView.as_view(), name="network_detail"),
    path("objects/ipaddress/", IPAddressListView.as_view(), name="ipaddress_list"),
    path("objects/ipaddress/<int:pk>/", IPAddressDetailView.as_view(), name="ipaddress_detail"),
    path("objects/hostname/", HostnameListView.as_view(), name="hostname_list"),
    path("objects/hostname/<int:pk>/", HostnameDetailView.as_view(), name="hostname_detail"),
]
