from http import HTTPStatus
from typing import Any

from django.http import JsonResponse
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
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
    Finding,
    FindingType,
    Hostname,
    IPAddress,
    IPPort,
    Network,
    Software,
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
    FindingSerializer,
    FindingTypeSerializer,
    HostnameSerializer,
    IPAddressSerializer,
    IPPortSerializer,
    NetworkSerializer,
    SoftwareSerializer,
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

    def create(self, request: Request, *args: Any, **kwargs: Any) -> JsonResponse:
        serializers = {serializer.Meta.model.__name__.lower(): serializer for serializer in self.serializers}
        response = {}

        for object_type, models in request.data.items():
            serializer_class = serializers[object_type.lower()]
            serializer = serializer_class(data=models, many=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            response[object_type] = serializer.data

        return JsonResponse(status=HTTPStatus.CREATED, data=response)


class FindingTypeViewSet(ManyModelViewSet):
    serializer_class = FindingTypeSerializer
    queryset = FindingType.objects.all()
    filterset_fields = ("code",)


class FindingViewSet(ManyModelViewSet):
    serializer_class = FindingSerializer
    queryset = Finding.objects.all()


class NetworkViewSet(ManyModelViewSet):
    serializer_class = NetworkSerializer
    queryset = Network.objects.all()
    filterset_fields = ("name",)


class HostnameViewSet(ManyModelViewSet):
    serializer_class = HostnameSerializer
    queryset = Hostname.objects.prefetch_related(
        "dnsarecord_set",
        "dnsaaaarecord_set",
        "dnscnamerecord_set",
        "dnsmxrecord_set",
        "dnsnsrecord_set",
        "dnsptrrecord_set",
        "dnscaarecord_set",
        "dnstxtrecord_set",
        "dnssrvrecord_set",
    )
    filterset_fields = ("name",)

    @action(detail=True, methods=["delete"], url_path="dnsrecord")
    def delete_dns_records(self, request: Request, pk: str | None = None) -> Response:
        hostname_id = pk
        record_ids = request.data.get("record_ids", [])
        total = 0

        if not record_ids or not isinstance(record_ids, list):
            return Response({"error": "record_ids should be a non-empty list"}, status=HTTPStatus.BAD_REQUEST)

        for model_cls in [
            DNSARecord,
            DNSAAAARecord,
            DNSCNAMERecord,
            DNSMXRecord,
            DNSNSRecord,
            DNSPTRRecord,
            DNSCAARecord,
            DNSTXTRecord,
            DNSSRVRecord,
        ]:
            qs = model_cls.objects.filter(hostname_id=hostname_id, id__in=record_ids)
            total += qs.count()
            qs.delete()

        return Response({"deleted": total}, status=HTTPStatus.OK)


class IPAddressViewSet(ManyModelViewSet):
    serializer_class = IPAddressSerializer
    queryset = IPAddress.objects.all()
    filterset_fields = ("address",)


class IPPortViewSet(ManyModelViewSet):
    serializer_class = IPPortSerializer
    queryset = IPPort.objects.all()
    filterset_fields = ("address", "protocol", "port", "tls", "service")


class SoftwareViewSet(ManyModelViewSet):
    serializer_class = SoftwareSerializer
    queryset = Software.objects.all()
    filterset_fields = ("name", "version", "cpi", "ports")


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
