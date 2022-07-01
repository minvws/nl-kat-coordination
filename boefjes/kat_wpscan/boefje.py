from boefjes.models import Boefje, Normalizer, SCAN_LEVEL

WPScan = Boefje(
    id="wp-scan",
    name="WPScan",
    description=("NEEDS API KEY IN ENV - Scan wordpress sites"),
    consumes={"SoftwareInstance"},
    produces={"Finding", "CVEFindingType"},
    scan_level=SCAN_LEVEL.L2,
)

BOEFJES = [WPScan]
NORMALIZERS = [
    Normalizer(
        name="kat_wpscan_normalize",
        module="kat_wpscan.normalize",
        consumes=[WPScan.id],
        produces=WPScan.produces,
    )
]
