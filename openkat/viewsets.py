from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from structlog import get_logger

from openkat.models import Indemnification, Organization
from openkat.serializers import OrganizationSerializer, OrganizationSerializerReadOnlyCode

logger = get_logger(__name__)


class OrganizationViewSet(viewsets.ModelViewSet):
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    # When we created this viewset we didn't have pagination enabled in the
    # django-rest-framework settings. Enabling it afterwards would cause the API
    # to change in an incompatible way, we should enable this when we introduce
    # a new API version.
    pagination_class = None

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
        # same endpoint to a different method, so we can't use the
        # permission_classes argument here.
        if not request.user.has_perm("openkat.view_organization"):
            raise PermissionDenied()

        organization = self.get_object()
        indemnification = Indemnification.objects.filter(organization=organization).first()

        if indemnification:
            return Response({"indemnification": True, "user": indemnification.user.pk})
        else:
            return Response({"indemnification": False, "user": None})

    @indemnification.mapping.post
    def set_indemnification(self, request, pk=None):
        if not request.user.has_perm("openkat.add_indemnification"):
            raise PermissionDenied()

        organization = self.get_object()

        indemnification = Indemnification.objects.filter(organization=organization).first()
        if indemnification:
            return Response({"indemnification": True, "user": indemnification.user.pk}, status=status.HTTP_409_CONFLICT)

        indemnification = Indemnification.objects.create(organization=organization, user=self.request.user)

        return Response({"indemnification": True, "user": indemnification.user.pk}, status=status.HTTP_201_CREATED)
