from http import HTTPStatus

from django.http import JsonResponse
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

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
from openkat.permissions import KATMultiModelPermissions
from openkat.viewsets import ManyModelViewSet


class ObjectViewSet(ViewSet):
    permission_classes = (KATMultiModelPermissions,)
    serializers = (
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

    def create(self, request: Request, *args, **kwargs):
        serializers = {serializer.Meta.model.__name__.lower(): serializer for serializer in self.serializers}
        response = {}

        for object_type, models in request.data.items():
            serializer_class = serializers[object_type.lower()]
            serializer = serializer_class(data=models, many=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            response[object_type] = serializer.data

        return JsonResponse(status=HTTPStatus.CREATED, data=response)


class NetworkViewSet(ManyModelViewSet):
    serializer_class = NetworkSerializer
    queryset = Network.objects.all()
    filterset_fields = ("name",)


class HostnameViewSet(ManyModelViewSet):
    serializer_class = HostnameSerializer
    queryset = Hostname.objects.all()
    filterset_fields = ("name",)


class IPAddressViewSet(ManyModelViewSet):
    serializer_class = IPAddressSerializer
    queryset = IPAddress.objects.all()
    filterset_fields = ("address",)


class IPPortViewSet(ManyModelViewSet):
    serializer_class = IPPortSerializer
    queryset = IPPort.objects.all()
    filterset_fields = ("address", "protocol", "port", "tls", "service")


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
