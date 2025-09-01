from datetime import datetime, timezone
from http import HTTPStatus

from django.conf import settings
from pydantic import TypeAdapter
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from structlog import get_logger

from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models.ooi.findings import Finding, FindingType
from octopoes.models.ooi.reports import AssetReport, BaseReport, HydratedReport, Report, ReportData, ReportRecipe
from octopoes.models.types import OOIType, get_collapsed_types
from openkat.forms.ooi_form import _EXCLUDED_OOI_TYPES
from openkat.models import Organization
from openkat.views.mixins import OOIList

logger = get_logger(__name__)
TYPE_ADAPTER = TypeAdapter(list[OOIType])


class ObjectCreateAPI(ViewSet):
    def get_queryset(self):
        # TODO: handle
        organization = Organization.objects.first()

        return OOIList(settings.OCTOPOES_FACTORY(organization.code), **self.get_queryset_params())

    def get_queryset_params(self):
        return {
            "valid_time": datetime.now(timezone.utc),
            "ooi_types": {t for t in get_collapsed_types().difference(
                {Finding, FindingType, BaseReport, Report, ReportRecipe, AssetReport, ReportData, HydratedReport}
            ) if t not in _EXCLUDED_OOI_TYPES},
            "scan_level": settings.DEFAULT_SCAN_LEVEL_FILTER,
            "scan_profile_type": settings.DEFAULT_SCAN_PROFILE_TYPE_FILTER,
            "search_string": "",
            "order_by": "scan_level" if self.request.GET.get("order_by", "") == "scan_level" else "object_type",
            "asc_desc": "desc" if self.request.GET.get("sorting_order", "") == "desc" else "asc",
        }

    def create(self, request: Request, *args, **kwargs):
        objects = request.data
        logger.info(objects=objects)
        organization = Organization.objects.first()

        client: OctopoesAPIConnector = settings.OCTOPOES_FACTORY(organization.code)
        now = datetime.now(timezone.utc)

        for ooi in TYPE_ADAPTER.validate_python(objects):
            client.octopoes.ooi_repository.save(ooi, valid_time=now)

        client.octopoes.commit()

        return Response(status=HTTPStatus.CREATED)
