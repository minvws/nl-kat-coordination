from http import HTTPStatus
from typing import Any

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
    Finding,
    FindingType,
    Hostname,
    IPAddress,
    IPPort,
    Network,
    Software,
    TaskObjects,
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
from tasks.models import Task


class TaskObjectMixin:
    def perform_create(self, serializer):
        objects = serializer.save()

        if "task_id" in self.request.GET:
            task = Task.objects.get(pk=self.request.GET["task_id"])
            task_objects, created = TaskObjects.objects.get_or_create(
                task_id=task.pk, defaults=dict(plugin_id=task.data["plugin_id"], input_objects=task.data["input_data"])
            )
            task_objects.output_objects.extend([str(obj) for obj in objects])
            task_objects.save()


class ObjectViewSet(ViewSet, TaskObjectMixin):
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
            self.perform_create(serializer)
            response[object_type] = serializer.data

        return JsonResponse(status=HTTPStatus.CREATED, data=response)


class FindingTypeViewSet(ManyModelViewSet, TaskObjectMixin):
    serializer_class = FindingTypeSerializer
    queryset = FindingType.objects.all()
    filterset_fields = ("code",)


class FindingViewSet(ManyModelViewSet, TaskObjectMixin):
    serializer_class = FindingSerializer
    queryset = Finding.objects.all()


class NetworkViewSet(ManyModelViewSet, TaskObjectMixin):
    serializer_class = NetworkSerializer
    queryset = Network.objects.all()
    filterset_fields = ("name",)


class HostnameViewSet(ManyModelViewSet, TaskObjectMixin):
    serializer_class = HostnameSerializer
    queryset = Hostname.objects.all()
    filterset_fields = ("name",)


class IPAddressViewSet(ManyModelViewSet, TaskObjectMixin):
    serializer_class = IPAddressSerializer
    queryset = IPAddress.objects.all()
    filterset_fields = ("address",)


class IPPortViewSet(ManyModelViewSet, TaskObjectMixin):
    serializer_class = IPPortSerializer
    queryset = IPPort.objects.all()
    filterset_fields = ("address", "protocol", "port", "tls", "service")


class SoftwareViewSet(ManyModelViewSet, TaskObjectMixin):
    serializer_class = SoftwareSerializer
    queryset = Software.objects.all()
    filterset_fields = ("name", "version", "cpi", "ports")


class DNSARecordViewSet(ManyModelViewSet, TaskObjectMixin):
    serializer_class = DNSARecordSerializer
    queryset = DNSARecord.objects.all()


class DNSAAAARecordViewSet(ManyModelViewSet, TaskObjectMixin):
    serializer_class = DNSAAAARecordSerializer
    queryset = DNSAAAARecord.objects.all()


class DNSPTRRecordViewSet(ManyModelViewSet, TaskObjectMixin):
    serializer_class = DNSPTRRecordSerializer
    queryset = DNSPTRRecord.objects.all()


class DNSCNAMERecordViewSet(ManyModelViewSet, TaskObjectMixin):
    serializer_class = DNSCNAMERecordSerializer
    queryset = DNSCNAMERecord.objects.all()


class DNSMXRecordViewSet(ManyModelViewSet, TaskObjectMixin):
    serializer_class = DNSMXRecordSerializer
    queryset = DNSMXRecord.objects.all()


class DNSNSRecordViewSet(ManyModelViewSet, TaskObjectMixin):
    serializer_class = DNSNSRecordSerializer
    queryset = DNSNSRecord.objects.all()


class DNSCAARecordViewSet(ManyModelViewSet, TaskObjectMixin):
    serializer_class = DNSCAARecordSerializer
    queryset = DNSCAARecord.objects.all()


class DNSTXTRecordViewSet(ManyModelViewSet, TaskObjectMixin):
    serializer_class = DNSTXTRecordSerializer
    queryset = DNSTXTRecord.objects.all()


class DNSSRVRecordViewSet(ManyModelViewSet, TaskObjectMixin):
    serializer_class = DNSSRVRecordSerializer
    queryset = DNSSRVRecord.objects.all()
