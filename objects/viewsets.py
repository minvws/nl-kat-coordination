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
)
from objects.serializers import (
    DNSAAAARecordSerializer,
    DNSARecordSerializer,
    DNSCAARecordSerializer,
    DNSCNAMERecordSerializer,
    DNSMXRecordSerializer,
    DNSNSRecordSerializer,
    DNSPTRRecordSerializer,
    DNSSRVRecordSerializer,
    DNSTXTRecordSerializer,
    HostnameSerializer,
    IPAddressSerializer,
    IPPortSerializer,
    NetworkSerializer,
)
from openkat.viewsets import ManyModelViewSet


class NetworkViewSet(ManyModelViewSet):
    serializer_class = NetworkSerializer
    queryset = Network.objects.all()


class HostnameViewSet(ManyModelViewSet):
    serializer_class = HostnameSerializer
    queryset = Hostname.objects.all()


class IPAddressViewSet(ManyModelViewSet):
    serializer_class = IPAddressSerializer
    queryset = IPAddress.objects.all()


class IPPortViewSet(ManyModelViewSet):
    serializer_class = IPPortSerializer
    queryset = IPPort.objects.all()


class DNSARecordViewSet(ManyModelViewSet):
    serializer_class = DNSARecordSerializer
    queryset = DNSARecord.objects.all()


class DNSAAAARecordViewSet(ManyModelViewSet):
    serializer_class = DNSAAAARecordSerializer
    queryset = DNSAAAARecord.objects.all()


class DNSPTRRecordViewSet(ManyModelViewSet):
    serializer_class = DNSPTRRecordSerializer
    queryset = DNSPTRRecord.objects.all()


class DNSCNAMERecordViewSet(ManyModelViewSet):
    serializer_class = DNSCNAMERecordSerializer
    queryset = DNSCNAMERecord.objects.all()


class DNSMXRecordViewSet(ManyModelViewSet):
    serializer_class = DNSMXRecordSerializer
    queryset = DNSMXRecord.objects.all()


class DNSNSRecordViewSet(ManyModelViewSet):
    serializer_class = DNSNSRecordSerializer
    queryset = DNSNSRecord.objects.all()


class DNSCAARecordViewSet(ManyModelViewSet):
    serializer_class = DNSCAARecordSerializer
    queryset = DNSCAARecord.objects.all()


class DNSTXTRecordViewSet(ManyModelViewSet):
    serializer_class = DNSTXTRecordSerializer
    queryset = DNSTXTRecord.objects.all()


class DNSSRVRecordViewSet(ManyModelViewSet):
    serializer_class = DNSSRVRecordSerializer
    queryset = DNSSRVRecord.objects.all()
