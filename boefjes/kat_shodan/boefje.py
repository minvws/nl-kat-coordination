from boefjes.models import Boefje, Normalizer

Shodan = Boefje(
    id="shodan",
    name="Shodan",
    description=(
        "NEEDS API KEY IN ENV - Use Shodan to find open ports with vulnerabilities that are found on that port"
    ),
    consumes={"IPAddressV4", "IPAddressV6"},
    produces={"IPPort", "Finding", "CVEFindingType"},
)


BOEFJES = [Shodan]
NORMALIZERS = [
    Normalizer(
        name="kat_shodan_normalize",
        module="kat_shodan.normalize",
        consumes=[Shodan.id],
        produces=Shodan.produces,
    )
]
