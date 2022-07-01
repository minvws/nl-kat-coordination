from boefjes.models import Boefje, Normalizer, SCAN_LEVEL

DNSSec = Boefje(
    id="dns-sec",
    name="Dnssec",
    description="Validates DNSSec of a hostname",
    consumes={"Hostname"},
    produces={"KATFindingType", "Finding"},
    scan_level=SCAN_LEVEL.L1,
)


BOEFJES = [DNSSec]
NORMALIZERS = [
    Normalizer(
        name="kat_dnssec_normalize",
        module="kat_dnssec.normalize",
        consumes=[DNSSec.id],
        produces=DNSSec.produces,
    )
]
