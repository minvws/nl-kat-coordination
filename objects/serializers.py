from rest_framework import serializers

from octopoes.models.types import OOIType


class ObjectSerializer(serializers.BaseSerializer):
    def to_representation(self, instance: OOIType):
        return instance.serialize()
