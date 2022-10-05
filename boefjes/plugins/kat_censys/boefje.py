from boefjes.plugins.models import Boefje, Normalizer

Censys = Boefje(
    id="censys",
    name="Censys",
    description=(
        "NEEDS API KEY IN ENV - Use Censys to discover open ports, services, certificates"
    ),
    consumes={"IPAddressV4", "IPAddressV6"},
    produces={"IPPort"},
)


BOEFJES = [Censys]
NORMALIZERS = [
    Normalizer(
        name="kat_censys_normalize",
        module="kat_censys.normalize",
        consumes=[Censys.id],
        produces=Censys.produces,
    )
]
