import uuid
from typing import Any, Dict

import factory
from factory import Factory, Faker, LazyFunction, PostGenerationMethodCall, Sequence, fuzzy
from scheduler.models import OOI, ScanProfile


class ScanProfileFactory(Factory):
    class Meta:
        model = ScanProfile

    level: int = fuzzy.FuzzyInteger(0, 4)

    scan_profile_type: str = Faker(
        "random_element",
        elements=["declared", "empty", "inherited"],
    )

    reference: str = Faker("uuid4")

    ooi_type: str = Faker(
        "random_element",
        elements=["Hostname", "Network"],
    )

    object_type: str = Faker(
        "random_element",
        elements=["Hostname", "Network"],
    )


class OOIFactory(Factory):
    class Meta:
        model = OOI

    primary_key: str = Sequence(lambda n: n)
    name: str = Faker("name")
    scan_profile: ScanProfile

    ooi_type: str = Faker(
        "random_element",
        elements=["Hostname", "Network"],
    )
