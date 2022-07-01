from boefjes.models import Boefje, Normalizer

Snyk = Boefje(
    id="snyk",
    name="Snyk.io-vulnerabilities",
    description="Get Snyk.io vulnerabilities based on Software",
    consumes={"SoftwareInstance"},
    produces={
        "SnykFindingType",
        "KATFindingType",
        "CVEFindingType",
        "Finding",
    },
)

BOEFJES = [Snyk]
NORMALIZERS = [
    Normalizer(
        name="kat_snyk_normalize",
        module="kat_snyk.normalize",
        consumes=[Snyk.id],
        produces=Snyk.produces,
    ),
]
