from rest_framework import serializers

from katalogus.models import Boefje


class BoefjeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Boefje
        fields = "__all__"
