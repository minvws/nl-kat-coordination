import base64
from datetime import datetime, timezone
from uuid import UUID

from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.urls import reverse
from pydantic_core import ValidationError
from rest_framework import viewsets
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.request import Request
from structlog import get_logger

from files.models import File, PluginContent
from katalogus.worker.interfaces import BoefjeInput, BoefjeOutput, StatusEnum
from katalogus.worker.interfaces import Task as WorkerTask
from tasks.models import Task, TaskResult, TaskStatus
from tasks.serializers import TaskSerializer

logger = get_logger(__name__)


class TaskViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = TaskSerializer
    queryset = Task.objects.all()


class BoefjeOutputViewSet(viewsets.ViewSet):
    # TODO: add permission classes again:
    permission_classes: list[BasePermission] = []

    def create(self, request: Request, task_id: UUID) -> HttpResponse:
        task = Task.objects.get(pk=task_id)
        task.status = TaskStatus.FAILED
        task.data["ended_at"] = str(datetime.now(timezone.utc))

        try:
            output = BoefjeOutput.model_validate(request.data)

            if output.status == StatusEnum.COMPLETED:
                task.status = TaskStatus.COMPLETED
        except ValidationError:
            return HttpResponseBadRequest("Invalid output")

        result = {}

        for file in output.files or []:
            raw = File.objects.create(
                file=PluginContent(base64.b64decode(file.content), task.data["boefje"]["plugin_id"]), type=file.type
            )
            TaskResult.objects.create(task=task, file=raw)

            result[file.name] = raw.id

        task.save()

        return JsonResponse(data=result)


class BoefjeInputViewSet(viewsets.ViewSet):
    # TODO: add permission classes again:
    permission_classes: list[BasePermission] = []

    def get(self, request: Request, task_id: UUID) -> HttpResponse:
        task = Task.objects.get(pk=task_id)

        if task.status != TaskStatus.RUNNING:
            return HttpResponseForbidden("Task does not have status running")

        output_url = f"{settings.OPENKAT_HOST}{reverse('boefje-output', args=(task_id,))}"
        boefje_input = BoefjeInput(output_url=output_url, task=WorkerTask.from_db(task))

        return JsonResponse(data=boefje_input.model_dump(mode="json"))
