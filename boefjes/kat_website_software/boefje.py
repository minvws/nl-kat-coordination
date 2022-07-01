from boefjes.models import Boefje, Normalizer, SCAN_LEVEL

WebsiteSoftware = Boefje(
    id="website-software",
    name="Wappalyzer - Software Scan",
    description="Scan for software on websites using Wappalyzer",
    consumes={"HostnameHTTPURL"},
    produces={"Software", "SoftwareInstance"},
    scan_level=SCAN_LEVEL.L2,
)


BOEFJES = [WebsiteSoftware]
NORMALIZERS = [
    Normalizer(
        name="kat_website_software_normalize",
        module="kat_website_software.normalize",
        consumes=[WebsiteSoftware.id],
        produces=WebsiteSoftware.produces,
    ),
]
