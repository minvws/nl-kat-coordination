from django.conf import settings
from katalogus.client import get_katalogus
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from structlog import get_logger

from octopoes.connector.octopoes import OctopoesAPIConnector
from tools.models import Indemnification, Organization
from tools.permissions import CanRecalculateBits, CanSetKatalogusSettings
from tools.serializers import OrganizationSerializer, OrganizationSerializerReadOnlyCode, ToOrganizationSerializer

logger = get_logger(__name__)


class OrganizationViewSet(viewsets.ModelViewSet):
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer

    # Unfortunately django-rest-framework doesn't have support for create only
    # fields so we have to change the serializer class depending on the request
    # method.
    def get_serializer_class(self):
        serializer_class = self.serializer_class
        if self.request.method != "POST":
            serializer_class = OrganizationSerializerReadOnlyCode
        return serializer_class

    @action(detail=True, permission_classes=[])
    def indemnification(self, request, pk=None):
        # DRF does not support different arguments when mapping POST/GET of the
        # same endpoind to a different method, so we can't use the
        # permission_classes argument here.
        if not request.user.has_perm("tools.view_organization"):
            raise PermissionDenied()

        organization = self.get_object()
        indemnification = Indemnification.objects.filter(organization=organization).first()

        if indemnification:
            return Response({"indemnification": True, "user": indemnification.user.pk})
        else:
            return Response({"indemnification": False, "user": None})

    @indemnification.mapping.post
    def set_indemnification(self, request, pk=None):
        if not request.user.has_perm("tools.add_indemnification"):
            raise PermissionDenied()

        organization = self.get_object()

        indemnification = Indemnification.objects.filter(organization=organization).first()
        if indemnification:
            return Response({"indemnification": True, "user": indemnification.user.pk}, status=status.HTTP_409_CONFLICT)

        indemnification = Indemnification.objects.create(organization=organization, user=self.request.user)

        return Response({"indemnification": True, "user": indemnification.user.pk}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], permission_classes=[CanRecalculateBits])
    def recalculate_bits(self, request, pk=None):
        organization = self.get_object()
        logger.info("Recalculating bits", event_code=920000, organization_code=self.organization.code)
        connector = OctopoesAPIConnector(settings.OCTOPOES_API, organization.code)
        number_of_bits = connector.recalculate_bits()

        return Response({"number_of_bits": number_of_bits})

    @action(detail=True, methods=["post"], permission_classes=[CanSetKatalogusSettings])
    def clone_katalogus_settings(self, request, pk=None):
        from_organization = self.get_object()

        serializer = ToOrganizationSerializer(data=request.data)
        if serializer.is_valid():
            to_organization = serializer.validated_data["to_organization"]
            logger.info(
                "Cloning organization settings",
                event_code=910000,
                organization_code=self.organization.code,
                to_organization_code=to_organization.code,
            )
            get_katalogus(from_organization.code).clone_all_configuration_to_organization(to_organization.code)

            return Response()
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
