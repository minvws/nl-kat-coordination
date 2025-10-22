from rest_framework import serializers
from rest_framework.fields import CharField, IntegerField
from rest_framework.relations import PrimaryKeyRelatedField, SlugRelatedField

from objects.models import (
    DNSAAAARecord,
    DNSARecord,
    DNSCAARecord,
    DNSCNAMERecord,
    DNSMXRecord,
    DNSNSRecord,
    DNSPTRRecord,
    DNSSRVRecord,
    DNSTXTRecord,
    Finding,
    FindingType,
    Hostname,
    IPAddress,
    IPPort,
    Network,
    Software,
)


class GetOrCreateSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        obj, created = self.Meta.model.objects.get_or_create(**validated_data)

        return obj


class FindingTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = FindingType
        exclude = ["_valid_from"]


def object_by_code(object_code: str | None, object_id: int | None, object_type: str) -> int | None:
    if not object_code:
        return object_id

    if object_type.lower() == "hostname":
        object_id = Hostname.objects.get(name=object_code).pk  # TODO: handle network
    if object_type.lower() == "ipaddress":
        object_id = IPAddress.objects.get(address=object_code).pk  # TODO: handle network
    if object_type.lower() == "network":
        object_id = Network.objects.get(name=object_code).pk

    return object_id


class FindingSerializer(serializers.ModelSerializer):
    finding_type = SlugRelatedField(slug_field="code", read_only=True)
    finding_type_code = CharField(write_only=True)
    object_code = CharField(write_only=True, required=False)
    object_id = IntegerField(required=False)

    def create(self, validated_data):
        object_id = object_by_code(
            validated_data.pop("object_code", None),
            validated_data.pop("object_id", None),
            validated_data["object_type"],
        )

        ft, created = FindingType.objects.get_or_create(code=validated_data.pop("finding_type_code"))
        f, created = Finding.objects.get_or_create(finding_type=ft, object_id=object_id, **validated_data)
        return f

    class Meta:
        model = Finding
        exclude = ["_valid_from"]


class NetworkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Network
        exclude = ["_valid_from"]


class HostnameSerializer(serializers.ModelSerializer):
    network = CharField(write_only=True)
    network_id = PrimaryKeyRelatedField(source="network", read_only=True)

    def create(self, validated_data):
        network_name = validated_data.pop("network")

        if not network_name:
            network_name = "internet"

        net, created = Network.objects.get_or_create(name=network_name)
        hn, created = Hostname.objects.get_or_create(network=net, **validated_data)
        return hn

    class Meta:
        model = Hostname
        exclude = ["_valid_from"]


class IPAddressSerializer(serializers.ModelSerializer):
    network = CharField(write_only=True)
    network_id = PrimaryKeyRelatedField(source="network", read_only=True)

    def create(self, validated_data):
        network_name = validated_data.pop("network")

        if not network_name:
            network_name = "internet"

        net, created = Network.objects.get_or_create(name=network_name)
        ip, created = IPAddress.objects.get_or_create(network=net, **validated_data)

        return ip

    class Meta:
        model = IPAddress
        exclude = ["_valid_from"]


class IPPortSerializer(GetOrCreateSerializer):
    class Meta:
        model = IPPort
        exclude = ["_valid_from"]


class SoftwareSerializer(GetOrCreateSerializer):
    class Meta:
        model = Software
        exclude = ["_valid_from"]


class DNSARecordSerializer(GetOrCreateSerializer):
    class Meta:
        model = DNSARecord
        exclude = ["_valid_from"]


class DNSAAAARecordSerializer(GetOrCreateSerializer):
    class Meta:
        model = DNSAAAARecord
        exclude = ["_valid_from"]


class DNSPTRRecordSerializer(GetOrCreateSerializer):
    class Meta:
        model = DNSPTRRecord
        exclude = ["_valid_from"]


class DNSCNAMERecordSerializer(GetOrCreateSerializer):
    class Meta:
        model = DNSCNAMERecord
        exclude = ["_valid_from"]


class DNSMXRecordSerializer(GetOrCreateSerializer):
    class Meta:
        model = DNSMXRecord
        exclude = ["_valid_from"]


class DNSNSRecordSerializer(GetOrCreateSerializer):
    class Meta:
        model = DNSNSRecord
        exclude = ["_valid_from"]


class DNSCAARecordSerializer(GetOrCreateSerializer):
    class Meta:
        model = DNSCAARecord
        exclude = ["_valid_from"]


class DNSTXTRecordSerializer(GetOrCreateSerializer):
    class Meta:
        model = DNSTXTRecord
        exclude = ["_valid_from"]


class DNSSRVRecordSerializer(GetOrCreateSerializer):
    class Meta:
        model = DNSSRVRecord
        exclude = ["_valid_from"]
