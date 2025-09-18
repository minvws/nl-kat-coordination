from rest_framework import serializers

from objects.models import Hostname, Network
from tasks.serializers import BulkCreateListSerializer


class NetworkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Network
        fields = "__all__"
        list_serializer_class = BulkCreateListSerializer


class HostnameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hostname
        fields = "__all__"
        list_serializer_class = BulkCreateListSerializer
