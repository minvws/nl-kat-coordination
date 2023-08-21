from factory import Factory, Faker
from scheduler.models import Normalizer


class NormalizerFactory(Factory):
    class Meta:
        model = Normalizer

    id: str = Faker("uuid4")
    name: str = Faker("name")
    description: str = Faker("text")
