from boefjes.models import Boefje, Normalizer, SCAN_LEVEL

SSLScan = Boefje(
    id="ssl-version",
    name="SSLScan",
    description="Scan SSL/TLS versions of websites",
    consumes={"Website"},
    produces={"KATFindingType", "Finding"},
    scan_level=SCAN_LEVEL.L2,
)

BOEFJES = [SSLScan]
NORMALIZERS = [
    Normalizer(
        name="kat_ssl_scan_normalize",
        module="kat_ssl_scan.normalize",
        consumes=[SSLScan.id],
        produces=SSLScan.produces,
    ),
]
