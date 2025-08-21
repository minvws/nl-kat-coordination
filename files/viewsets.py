from rest_framework import viewsets
from rest_framework.permissions import BasePermission
from structlog import get_logger

from files.models import File
from files.serializers import FileSerializer

logger = get_logger(__name__)


class FileViewSet(viewsets.ModelViewSet):
    # TODO: add permission classes again
    permission_classes: list[BasePermission] = []
    serializer_class = FileSerializer
    queryset = File.objects.all()
