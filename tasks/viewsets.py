from structlog import get_logger

from openkat.viewsets import ManyModelViewSet
from tasks.models import Task
from tasks.serializers import TaskSerializer

logger = get_logger(__name__)


class TaskViewSet(ManyModelViewSet):
    serializer_class = TaskSerializer
    queryset = Task.objects.all()
