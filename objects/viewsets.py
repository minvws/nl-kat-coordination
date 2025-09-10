from datetime import datetime, timezone
from http import HTTPStatus

from django.conf import settings
from pydantic import TypeAdapter
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from structlog import get_logger

from objects.serializers import ObjectSerializer
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import Reference
from octopoes.models.types import OOIType, type_by_name
from octopoes.xtdb.query import InvalidField, Query
from openkat.models import Organization

logger = get_logger(__name__)
OOI_TYPE_LIST = TypeAdapter(list[OOIType])
REF_LIST = TypeAdapter(list[Reference])


class ObjectViewSet(ViewSet):
    def list(self, request, *args, **kwargs):
        if "object_type" in request.GET:
            q = Query(type_by_name(request.GET["object_type"]))
        else:
            q = Query()

        for parameter, value in request.GET.items():
            if parameter == "object_type":
                continue
            if parameter == "offset":
                q = q.offset(int(value))
                continue
            if parameter == "limit":
                q = q.limit(int(value))
                continue

            try:
                q = q.where(q.result_type, **{parameter: value})
            except InvalidField:
                logger.debug("Invalid field for query", result_type=q.result_type, parameter=parameter)
                continue

        # TODO
        organization = Organization.objects.first()
        connector: OctopoesAPIConnector = settings.OCTOPOES_FACTORY(organization.code)

        oois = connector.octopoes.ooi_repository.query(q, datetime.now(timezone.utc))
        serializer = ObjectSerializer(oois, many=True)

        return Response(serializer.data)

    def create(self, request: Request, *args, **kwargs):
        objects = request.data
        organization = Organization.objects.first()

        client: OctopoesAPIConnector = settings.OCTOPOES_FACTORY(organization.code)
        now = datetime.now(timezone.utc)

        for ooi in OOI_TYPE_LIST.validate_python(objects):
            client.octopoes.ooi_repository.save(ooi, valid_time=now)

        client.octopoes.commit()

        return Response(status=HTTPStatus.CREATED)

    def delete(self, request: Request, *args, **kwargs):
        objects = request.data
        organization = Organization.objects.first()

        client: OctopoesAPIConnector = settings.OCTOPOES_FACTORY(organization.code)
        now = datetime.now(timezone.utc)

        for ooi in REF_LIST.validate_python(objects):
            client.octopoes.ooi_repository.delete(ooi, valid_time=now)

        client.octopoes.commit()

        return Response(status=HTTPStatus.CREATED)
