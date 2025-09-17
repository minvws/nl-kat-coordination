from rest_framework import viewsets

from objects.models import Hostname, Network
from objects.serializers import HostnameSerializer, NetworkSerializer


class NetworkViewSet(viewsets.ModelViewSet):
    serializer_class = NetworkSerializer
    queryset = Network.objects.all()


class HostnameViewSet(viewsets.ModelViewSet):
    serializer_class = HostnameSerializer
    queryset = Hostname.objects.all()
    filterset_fields = ("network__name",)
