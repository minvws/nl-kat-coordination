from boefjes.plugins.models import Boefje, Normalizer, SCAN_LEVEL

Dummy = Boefje(
    id="kat_test",
    name="Kat test name",
    description="Testing KAT",
    consumes={"DNSZone"},
    produces={"Certificate", "Hostname"},
    scan_level=SCAN_LEVEL.L1,
)

BOEFJES = [Dummy]
NORMALIZERS = [
    Normalizer(
        name="kat_test_normalize", module="kat_crt_sh.normalize", consumes=["text/html"]
    ),
]
