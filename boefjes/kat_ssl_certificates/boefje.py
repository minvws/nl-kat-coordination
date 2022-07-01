from boefjes.models import Boefje, Normalizer

SSLCertificate = Boefje(
    id="ssl-certificates",
    name="SSLCertificates",
    description="Scan SSL certificates of websites",
    consumes={"Website"},
    produces={"Certificate"},
)


BOEFJES = [SSLCertificate]
NORMALIZERS = [
    Normalizer(
        name="kat_ssl_certificates_normalize",
        module="kat_ssl_certificates.normalize",
        consumes=[SSLCertificate.id],
        produces=SSLCertificate.produces,
    ),
]
