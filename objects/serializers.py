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
    ScanLevel,
)
from tasks.serializers import BulkCreateListSerializer


class FindingTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = FindingType
        fields = "__all__"
        list_serializer_class = BulkCreateListSerializer


class FindingCreateListSerializer(serializers.ListSerializer):
    def create(self, validated_data):
        by_code = {}
        for item in validated_data:
            ft, created = FindingType.objects.get_or_create(code=item["finding_type_code"])
            by_code[item["finding_type_code"]] = ft

        bulk = []
        for item in validated_data:
            object_id = object_by_code(item.pop("object_code", None), item.pop("object_id", None), item["object_type"])
            finding_type = by_code[item.pop("finding_type_code")]
            bulk.append(Finding(finding_type=finding_type, object_id=object_id, **item))

        return self.child.Meta.model.objects.bulk_create(bulk)


def object_by_code(object_code: str | None, object_id: int | None, object_type: str):
    if not object_code:
        return object_id

    if object_type.lower() == "hostname":
        object_id = Hostname.objects.get(name=object_code).id  # TODO: handle network
    if object_type.lower() == "ipaddress":
        object_id = IPAddress.objects.get(address=object_code).id  # TODO: handle network
    if object_type.lower() == "network":
        object_id = Network.objects.get(name=object_code).id

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

        return Finding.objects.create(
            finding_type=FindingType.objects.get(code=validated_data.pop("finding_type_code")),
            object_id=object_id,
            **validated_data,
        )

    class Meta:
        model = Finding
        fields = "__all__"
        list_serializer_class = FindingCreateListSerializer


class NetworkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Network
        fields = "__all__"
        list_serializer_class = BulkCreateListSerializer


class QueryRelatedNetworkListSerializer(serializers.ListSerializer):
    def create(self, validated_data):
        """Inspired by the standard create method"""

        network_names = {item["network"] for item in validated_data}
        networks = {}

        for name in network_names:
            net, created = Network.objects.get_or_create(name=name)
            networks[net.name] = net

        bulk = []
        for item in validated_data:
            network = item.pop("network")
            bulk.append(self.child.Meta.model(network=networks[network], **item))

        return self.child.Meta.model.objects.bulk_create(bulk)


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
        fields = "__all__"
        list_serializer_class = QueryRelatedNetworkListSerializer


class ScanLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScanLevel
        fields = "__all__"
        list_serializer_class = BulkCreateListSerializer


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
        fields = "__all__"
        list_serializer_class = QueryRelatedNetworkListSerializer


class IPPortSerializer(serializers.ModelSerializer):
    class Meta:
        model = IPPort
        fields = "__all__"
        list_serializer_class = BulkCreateListSerializer


class DNSARecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = DNSARecord
        fields = "__all__"
        list_serializer_class = BulkCreateListSerializer


class DNSAAAARecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = DNSAAAARecord
        fields = "__all__"
        list_serializer_class = BulkCreateListSerializer


class DNSPTRRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = DNSPTRRecord
        fields = "__all__"
        list_serializer_class = BulkCreateListSerializer


class DNSCNAMERecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = DNSCNAMERecord
        fields = "__all__"
        list_serializer_class = BulkCreateListSerializer


class DNSMXRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = DNSMXRecord
        fields = "__all__"
        list_serializer_class = BulkCreateListSerializer


class DNSNSRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = DNSNSRecord
        fields = "__all__"
        list_serializer_class = BulkCreateListSerializer


class DNSCAARecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = DNSCAARecord
        fields = "__all__"
        list_serializer_class = BulkCreateListSerializer


class DNSTXTRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = DNSTXTRecord
        fields = "__all__"
        list_serializer_class = BulkCreateListSerializer


class DNSSRVRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = DNSSRVRecord
        fields = "__all__"
        list_serializer_class = BulkCreateListSerializer
