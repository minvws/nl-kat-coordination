from bits.check_greeting.check_greeting import run as run_check_greeting

from octopoes.models.ooi.findings import Finding, FindingType
from octopoes.models.ooi.greeting import Greeting
from octopoes.models.ooi.network import IPAddressV4


def test_check_greeting():
    address = IPAddressV4(address="8.8.8.8", network="fake")
    greeting = Greeting(address=address.reference, greeting="HelloThere😺")
    results: tuple[FindingType, Finding] = list(run_check_greeting(greeting, [], {}))
    assert len(results) == 2

    findingType, finding = results

    assert isinstance(findingType, FindingType)
    assert findingType.id == "KAT-GREETING"

    assert isinstance(finding, Finding)
