from factory import Factory
from scheduler.models import Job


class JobFactory(Factory):
    class Meta:
        model = Job
