from boefjes.models import Boefje, Normalizer


GreenHosting = Boefje(
    id="green-hosting",
    module="kat_green_hosting.scan",
    name="GreenHosting",
    description="Use the Green Web Foundation Partner API to check whether the website is hosted on a green server. Meaning it runs on renewable energy and/or offsets its carbon footprint",
    consumes={"Website"},
    produces=["KATFindingType", "Finding"],
)

BOEFJES = [GreenHosting]
NORMALIZERS = [
    Normalizer(
        name="kat_green_hosting_normalize",
        module="kat_green_hosting.normalize",
        consumes=[GreenHosting.id],
        produces=GreenHosting.produces,
    ),
]
