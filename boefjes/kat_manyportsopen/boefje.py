from boefjes.models import Boefje, Normalizer

ManyPortsOpen = Boefje(
    id="many-ports-open",
    name="Many new ports open",
    description="Check if there are many ports open that were not before",
    consumes={"IPAddressV4", "IPAddressV6"},
    produces={"KATFindingType", "Finding"},
)

BOEFJES = [ManyPortsOpen]
NORMALIZERS = [
    Normalizer(
        name="kat_manyportsopen_normalize",
        module="kat_manyportsopen.normalize",
        consumes=[ManyPortsOpen.id],
        produces=ManyPortsOpen.produces,
    ),
]
