from rest_framework import serializers
from rest_framework.utils import model_meta

from tasks.models import Task, TaskResult


class BulkCreateListSerializer(serializers.ListSerializer):
    def create(self, validated_data):
        """Inspired by the standard create method"""

        ModelClass = self.child.Meta.model
        info = model_meta.get_field_info(ModelClass)
        many_to_many = {}
        for field_name, relation_info in info.relations.items():
            if relation_info.to_many and (field_name in validated_data):
                many_to_many[field_name] = validated_data.pop(field_name)

        bulk = [ModelClass(**item) for item in validated_data]
        instances = ModelClass.objects.bulk_create(bulk)

        # Save many-to-many relationships after the instance is created.
        if many_to_many:
            for instance in instances:
                for field_name, value in many_to_many.items():
                    field = getattr(instance, field_name)
                    field.set(value)

        return instances


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = "__all__"
        list_serializer_class = BulkCreateListSerializer


class TaskResultSerializer(serializers.ModelSerializer):
    task = TaskSerializer(read_only=True)

    class Meta:
        model = TaskResult
        fields = "__all__"
