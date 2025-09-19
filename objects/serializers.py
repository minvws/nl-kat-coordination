from rest_framework import serializers

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
    Hostname,
    IPAddress,
    IPPort,
    Network,
    ScanLevel,
)
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


class ScanLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScanLevel
        fields = "__all__"
        list_serializer_class = BulkCreateListSerializer


class IPAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = IPAddress
        fields = "__all__"
        list_serializer_class = BulkCreateListSerializer


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


