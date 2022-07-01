from boefjes.models import Boefje, Normalizer, SCAN_LEVEL

Fierce = Boefje(
    id="fierce",
    name="Fierce",
    description="Use a Fierce scan to find subdomains (with their ip)",
    consumes={"Hostname"},
    produces={"Hostname", "IPAddressV4", "IPAddressV6", "DNSARecord", "DNSAAAARecord"},
    scan_level=SCAN_LEVEL.L2,
)
BOEFJES = [Fierce]
NORMALIZERS = [
    Normalizer(
        name="kat_fierce_normalize",
        module="kat_fierce.normalize",
        consumes=[Fierce.id],
        produces=Fierce.produces,
    ),
]
