from rest_framework import serializers

from files.models import File
from tasks.serializers import TaskResultSerializer


class FileSerializer(serializers.ModelSerializer):
    task_result = TaskResultSerializer(read_only=True)

    class Meta:
        model = File
        fields = "__all__"
