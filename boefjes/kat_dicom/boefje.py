from boefjes.models import Boefje, Normalizer, SCAN_LEVEL

DICOM = Boefje(
    id="dicom",
    name="DICOM",
    description="Find exposed DICOM servers.",
    consumes={"IPAddressV4", "IPAddressV6"},
    produces={"IPPort", "Software", "SoftwareInstance", "KATFindingType", "Finding"},
    scan_level=SCAN_LEVEL.L2,
)

BOEFJES = [DICOM]
NORMALIZERS = [
    Normalizer(
        name="kat_dicom_normalize",
        module="kat_dicom.normalize",
        consumes=[DICOM.id],
        produces=DICOM.produces,
    )
]
