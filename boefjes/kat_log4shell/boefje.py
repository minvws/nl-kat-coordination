from boefjes.models import Boefje, SCAN_LEVEL

Log4Shell = Boefje(
    id="log4shell",
    name="Log4Shell",
    description="Check for Log4j vulnerability. This boefje will not create a finding. We will contact you if needed.",
    consumes={"Hostname"},
    produces={"CVEFindingType", "Finding"},
    scan_level=SCAN_LEVEL.L3,
)

BOEFJES = [Log4Shell]
NORMALIZERS = []
