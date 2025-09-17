from rest_framework import serializers

from objects.models import Network, Hostname


class NetworkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Network
        fields = "__all__"


class HostnameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hostname
        fields = "__all__"
