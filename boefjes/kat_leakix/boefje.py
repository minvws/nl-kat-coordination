from boefjes.models import Boefje, Normalizer

LeakIX = Boefje(
    id="leakix",
    name="LeakIX",
    description="Use LeakIX to find open ports, software and vulnerabilities",
    consumes={"IPAddressV4", "IPAddressV6", "Hostname"},
    produces={
        "IPService",
        "IPPort",
        "Service",
        "Software",
        "SoftwareInstance",
        "CVEFindingType",
        "KATFindingType",
        "Finding",
    },
)


BOEFJES = [LeakIX]
NORMALIZERS = [
    Normalizer(
        name="kat_leakix_normalize",
        module="kat_leakix.normalize",
        consumes=[LeakIX.id],
        produces=LeakIX.produces,
    ),
]
