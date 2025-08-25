from rest_framework import viewsets
from structlog import get_logger

from files.models import File
from files.serializers import FileSerializer

logger = get_logger(__name__)


class FileViewSet(viewsets.ModelViewSet):
    serializer_class = FileSerializer
    queryset = File.objects.all()
