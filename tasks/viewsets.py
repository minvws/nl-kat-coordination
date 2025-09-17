from rest_framework import viewsets
from structlog import get_logger

from tasks.models import Task
from tasks.serializers import TaskSerializer

logger = get_logger(__name__)


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    queryset = Task.objects.all()
