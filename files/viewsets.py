from rest_framework import viewsets
from structlog import get_logger

from files.models import File
from files.serializers import FileSerializer
from tasks.models import TaskResult

logger = get_logger(__name__)


class FileViewSet(viewsets.ModelViewSet):
    serializer_class = FileSerializer
    queryset = File.objects.all()

    def perform_create(self, serializer):
        file = serializer.save()

        if "task_id" in self.request.GET:
            TaskResult.objects.create(file=file, task_id=self.request.GET["task_id"])
