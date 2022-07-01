from factory import Factory, Faker
from scheduler.models import Organisation


class OrganisationFactory(Factory):
    class Meta:
        model = Organisation

    id: str = Faker("uuid4")
    name: str = Faker("company")
