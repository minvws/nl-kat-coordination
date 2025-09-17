from rest_framework import serializers

from objects.models import Network


class NetworkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Network
        fields = "__all__"
