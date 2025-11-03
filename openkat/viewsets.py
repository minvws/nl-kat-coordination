from http import HTTPStatus
from typing import Any
from urllib.request import Request

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


class ManyModelViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        if "id" in self.request.GET:
            return super().get_queryset().filter(id__in=self.request.GET.getlist("id"))

        return super().get_queryset()

    def delete(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        queryset = self.get_queryset()
        count = queryset.count()

        if count == 0:
            return Response({"deleted": count}, status=HTTPStatus.OK)

        queryset.delete()

        return Response({"deleted": count}, status=HTTPStatus.OK)

    def get_serializer(self, *args, **kwargs):
        if isinstance(kwargs.get("data", {}), list):
            kwargs["many"] = True

        return super().get_serializer(*args, **kwargs)
