from boefjes.models import Boefje, Normalizer, SCAN_LEVEL

WebsiteSimilarity = Boefje(
    id="website-similarity",
    name="Website similarity",
    description="Check if the websites hosted on IPv4 and IPv6 are the same",
    consumes={"Hostname"},
    produces={"KATFindingType", "Finding"},
    scan_level=SCAN_LEVEL.L2,
)


BOEFJES = [WebsiteSimilarity]
NORMALIZERS = [
    Normalizer(
        name="kat_website_similarity_normalize",
        module="kat_website_similarity.normalize",
        consumes=[WebsiteSimilarity.id],
        produces=WebsiteSimilarity.produces,
    ),
]
