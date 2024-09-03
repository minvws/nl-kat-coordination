from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from tools.models import Indemnification, Organization
from tools.serializers import OrganizationSerializer, OrganizationSerializerReadOnlyCode


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

    @action(detail=True)
    def indemnification(self, request, pk=None):
        organization = self.get_object()
        indemnification = Indemnification.objects.filter(organization=organization).first()

        if indemnification:
            return Response({"indemnification": True, "user": indemnification.user.pk})
        else:
            return Response({"indemnification": False, "user": None})

    @indemnification.mapping.post
    def set_indemnification(self, request, pk=None):
        organization = self.get_object()

        indemnification = Indemnification.objects.filter(organization=organization).first()
        if indemnification:
            return Response({"indemnification": True, "user": indemnification.user.pk}, status=status.HTTP_409_CONFLICT)

        indemnification = Indemnification.objects.create(organization=organization, user=self.request.user)

        return Response({"indemnification": True, "user": indemnification.user.pk}, status=status.HTTP_201_CREATED)
