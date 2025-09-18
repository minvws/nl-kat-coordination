from rest_framework import viewsets

from objects.models import Hostname, Network
from objects.serializers import HostnameSerializer, NetworkSerializer


class NetworkViewSet(viewsets.ModelViewSet):
    serializer_class = NetworkSerializer
    queryset = Network.objects.all()

    def get_serializer(self, *args, **kwargs):
        if isinstance(kwargs.get("data", {}), list):
            kwargs["many"] = True

        return super().get_serializer(*args, **kwargs)


class HostnameViewSet(viewsets.ModelViewSet):
    serializer_class = HostnameSerializer
    queryset = Hostname.objects.all()
    filterset_fields = ("network__name",)

    def get_serializer(self, *args, **kwargs):
        if isinstance(kwargs.get("data", {}), list):
            kwargs["many"] = True

        return super().get_serializer(*args, **kwargs)
