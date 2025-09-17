from rest_framework import viewsets

from objects.models import Network
from objects.serializers import NetworkSerializer


class NetworkViewSet(viewsets.ModelViewSet):
    serializer_class = NetworkSerializer
    queryset = Network.objects.all()
