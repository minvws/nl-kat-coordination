from django.db import models
from django.db.models import QuerySet


class Object(models.Model):
    type = models.CharField(max_length=64, unique=True)
    value = models.TextField()


class ObjectSet(models.Model):
    """ Composite-like model representing a set of objects that can be used as an input for tasks """

    name = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True)
    dynamic = models.BooleanField(default=False)
    object_query = models.TextField(null=True, blank=True)

    # can hold both objects and other groups (composite pattern)
    all_objects = models.ManyToManyField(Object, blank=True, related_name="object_sets")
    subsets = models.ManyToManyField("self", blank=True, symmetrical=False, related_name="supersets")

    def traverse_objects(self, depth: int = 0, max_depth: int = 3) -> QuerySet[Object]:
        # TODO: handle cycles
        # TODO: configurable max_depth

        if depth >= max_depth:
            raise RecursionError("Max depth reached for object set.")

        all_objects = self.all_objects.all()

        for subset in self.subsets.all():
            all_objects = all_objects.union(subset.traverse_objects(depth + 1, max_depth))

        return all_objects

    def __str__(self):
        return self.name or super().__str__()
