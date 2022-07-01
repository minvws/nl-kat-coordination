from boefjes.models import Boefje, Normalizer, SCAN_LEVEL

CRTBoefje = Boefje(
    id="certificate-search",
    name="CRT",
    description="Certificate search",
    consumes={"DNSZone"},
    produces={"Certificate", "Hostname"},
    scan_level=SCAN_LEVEL.L1,
)

BOEFJES = [CRTBoefje]
NORMALIZERS = [
    Normalizer(
        name="kat_crt_sh_normalize",
        module="kat_crt_sh.normalize",
        consumes=[CRTBoefje.id],
        produces=CRTBoefje.produces,
    )
]
