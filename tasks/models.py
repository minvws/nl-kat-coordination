import uuid

from django.db import models

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


class Schedule(models.Model):
    type = models.CharField(max_length=64)
    organization = models.ForeignKey("openkat.organization", on_delete=models.CASCADE, related_name="schedules")
    data = models.JSONField(default=dict)
    enabled = models.BooleanField(default=True)
    schedule = models.CharField(max_length=32, null=True)

    deadline_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)


class Task(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name="tasks", null=True)
    organization = models.ForeignKey("openkat.organization", on_delete=models.CASCADE, related_name="tasks", null=True)
    type = models.CharField(max_length=32)
    priority = models.IntegerField(default=1)
    data = models.JSONField(default=dict)
    status = models.CharField(max_length=16, choices=TaskStatus.choices, default=TaskStatus.PENDING)

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)


class TaskResult(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="task_results")
    file = models.OneToOneField(File, on_delete=models.CASCADE, related_name="task_result")
