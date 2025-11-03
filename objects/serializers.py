from typing import Any

from rest_framework import serializers
from rest_framework.fields import CharField, SerializerMethodField
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


class FindingSerializer(serializers.ModelSerializer):
    finding_type = SlugRelatedField(slug_field="code", read_only=True)
    finding_type_code = CharField(write_only=True)

    hostname = CharField(write_only=True, required=False, allow_null=True)
    ipaddress = CharField(write_only=True, required=False, allow_null=True)

    hostname_id = PrimaryKeyRelatedField(source="hostname", read_only=True)
    address_id = PrimaryKeyRelatedField(source="address", read_only=True)

    def create(self, validated_data):
        hostname_name = validated_data.pop("hostname", None)
        ipaddress_str = validated_data.pop("ipaddress", None)

        hostname_obj = None
        address_obj = None

        if hostname_name:
            hostname_obj = Hostname.objects.get(name=hostname_name)
        elif ipaddress_str:
            address_obj = IPAddress.objects.get(address=ipaddress_str)

        ft, created = FindingType.objects.get_or_create(code=validated_data.pop("finding_type_code"))
        f, created = Finding.objects.get_or_create(
            finding_type=ft, hostname=hostname_obj, address=address_obj, **validated_data
        )
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
    dns_records = SerializerMethodField(read_only=True)

    def create(self, validated_data):
        network_name = validated_data.pop("network")

        if not network_name:
            network_name = "internet"

        net, created = Network.objects.get_or_create(name=network_name)
        hn, created = Hostname.objects.get_or_create(network=net, **validated_data)
        return hn

    def get_dns_records(self, obj: Hostname) -> list[dict[str, Any]]:
        dns = []

        for field, serializer_class in [
            (obj.dnsarecord_set, DNSARecordSerializer),
            (obj.dnsaaaarecord_set, DNSAAAARecordSerializer),
            (obj.dnscnamerecord_set, DNSCNAMERecordSerializer),
            (obj.dnsmxrecord_set, DNSMXRecordSerializer),
            (obj.dnstxtrecord_set, DNSTXTRecordSerializer),
            (obj.dnsnsrecord_set, DNSNSRecordSerializer),
            (obj.dnsptrrecord_set, DNSPTRRecordSerializer),
            (obj.dnscaarecord_set, DNSCAARecordSerializer),
            (obj.dnssrvrecord_set, DNSSRVRecordSerializer),
        ]:
            serializer = serializer_class(data=list(field.all()), many=True)
            serializer.is_valid()
            dns.extend([dns | {"object_type": serializer_class.Meta.model.__name__.lower()} for dns in serializer.data])

        return dns

    class Meta:
        model = Hostname
        exclude = ["_valid_from"]


class SoftwareSerializer(GetOrCreateSerializer):
    class Meta:
        model = Software
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
    address = CharField(write_only=True)
    address_id = PrimaryKeyRelatedField(source="address", read_only=True)
    software = SoftwareSerializer(many=True, default=[])

    def create(self, validated_data):
        address = validated_data.pop("address")

        ip, created = IPAddress.objects.get_or_create(address=address)

        port = validated_data.pop("port")
        software = validated_data.pop("software")
        ipport, created = IPPort.objects.get_or_create(address=ip, port=port, defaults=validated_data)

        for s in software:
            name = s.pop("name")
            obj, created = Software.objects.get_or_create(name=name, defaults=s)
            ipport.software.add(obj)

        return ipport

    class Meta:
        model = IPPort
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
