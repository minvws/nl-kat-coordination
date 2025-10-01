import uuid

import recurrence.fields
from celery import Celery
from celery.result import AsyncResult
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import ArrayField
from django.db import models
from djangoql.queryset import apply_search

from files.models import File


class TaskStatus(models.TextChoices):
    # Task has been created but not yet queued
    PENDING = "pending"

    # Task has been pushed onto queue and is ready to be picked up
    QUEUED = "queued"

    # Task has been picked up by a worker
    DISPATCHED = "dispatched"

    # Task has been picked up by a worker, and the worker indicates that it is
    # running.
    RUNNING = "running"

    # Task has been completed
    COMPLETED = "completed"

    # Task has failed
    FAILED = "failed"

    # Task has been cancelled
    CANCELLED = "cancelled"


class Operation(models.TextChoices):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class ObjectSet(models.Model):
    """Composite-like model representing a set of objects that can be used as an input for tasks"""

    # TODO: organization field?
    name = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True)
    dynamic = models.BooleanField(default=False)  # TODO
    object_type: models.ForeignKey = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_query = models.TextField(null=True, blank=True)

    # can hold both objects and other groups (composite pattern)
    all_objects = ArrayField(models.BigIntegerField(), default=list, blank=True)
    subsets = models.ManyToManyField("self", blank=True, symmetrical=False, related_name="supersets")

    def get_query_objects(self) -> list[int]:
        """Get objects from object_query using DjangoQL"""
        if not self.object_query:
            return []

        try:
            # Get the model class from the content type
            model_class = self.object_type.model_class()

            # Apply the DjangoQL query
            queryset = apply_search(model_class.objects.all(), self.object_query, model_class)

            # Return primary keys as integers
            return [obj.pk for obj in queryset]
        except Exception:
            # If query fails, return empty list
            return []

    def traverse_objects(self, depth: int = 0, max_depth: int = 3) -> list[int]:
        # TODO: handle cycles
        # TODO: configurable max_depth

        # Start with manually added objects from all_objects field
        all_objects = list(self.all_objects)

        # Add objects from object_query
        query_objects = self.get_query_objects()
        all_objects.extend(query_objects)

        # Add objects from subsets if we haven't exceeded max depth
        if depth < max_depth:
            for subset in self.subsets.all():
                all_objects.extend(subset.traverse_objects(depth + 1, max_depth))

        # Remove duplicates while preserving order
        seen = set()
        unique_objects = []
        for obj in all_objects:
            if obj not in seen:
                seen.add(obj)
                unique_objects.append(obj)

        return unique_objects

    def __str__(self):
        return self.name or super().__str__()


class Schedule(models.Model):
    enabled = models.BooleanField(default=True)
    recurrences = recurrence.fields.RecurrenceField(null=True, blank=True)

    # TODO: multiple organizations?
    organization = models.ForeignKey(
        "openkat.organization", on_delete=models.CASCADE, related_name="schedules", null=True, blank=True
    )
    plugin = models.ForeignKey("plugins.plugin", on_delete=models.CASCADE, related_name="schedules", null=True)
    object_set = models.ForeignKey(ObjectSet, on_delete=models.CASCADE, related_name="schedules", null=True, blank=True)

    run_on = models.CharField(max_length=64, null=True, blank=True)
    operation = models.CharField(max_length=16, choices=Operation, null=True, blank=True)

    def run(self):
        # Import here to prevent circular imports
        from tasks.tasks import run_schedule  # noqa: PLC0415

        run_schedule(self)


class Task(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    schedule = models.ForeignKey(Schedule, on_delete=models.SET_NULL, related_name="tasks", null=True, blank=True)
    organization = models.ForeignKey(
        "openkat.organization", on_delete=models.CASCADE, related_name="tasks", null=True, blank=True
    )
    type = models.CharField(max_length=32, default="plugin")
    data = models.JSONField(default=dict)
    status = models.CharField(max_length=16, choices=TaskStatus, default=TaskStatus.PENDING)

    created_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True)
    modified_at = models.DateTimeField(auto_now=True)

    _async_result: AsyncResult | None = None

    @property
    def async_result(self, celery: Celery | None = None) -> AsyncResult:
        if self._async_result is not None:
            return self._async_result

        if not celery:
            from tasks.celery import app  # noqa: PLC0415

            celery = app

        self._async_result = AsyncResult(str(self.id), app=celery)

        return self._async_result

    def cancel(self):
        # Import here to prevent circular imports
        from tasks.celery import app  # noqa: PLC0415

        self.status = TaskStatus.CANCELLED
        self.save()
        app.control.revoke(str(self.id), terminate=True)

    def done(self) -> bool:
        return self.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]


class TaskResult(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="task_results")
    file = models.OneToOneField(File, on_delete=models.CASCADE, related_name="task_result")
