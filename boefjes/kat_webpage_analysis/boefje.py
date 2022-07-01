from boefjes.models import Boefje, Normalizer, SCAN_LEVEL

WebpageAnalysis = Boefje(
    id="webpage-analysis",
    name="WebpageAnalysis",
    description="Downloads a resource and uses several different normalizers to analyze",
    consumes={"HTTPResource"},
    dispatches={
        "normalizers": ["kat_webpage_analysis_headers_normalize"],
        "boefjes": [],
    },
    produces={"HTTPHeader"},
    scan_level=SCAN_LEVEL.L2,
)

BOEFJES = [WebpageAnalysis]
NORMALIZERS = [
    Normalizer(
        name="kat_webpage_analysis_headers_normalize",
        module="kat_webpage_analysis.headers_normalize",
        consumes=[WebpageAnalysis.id],
        produces=WebpageAnalysis.produces,
    ),
]
