import datetime
from collections.abc import Iterator

from octopoes.models import OOI
from octopoes.models.ooi.certificate import X509Certificate
from octopoes.models.ooi.config import Config
from octopoes.models.ooi.findings import Finding, KATFindingType


def nibble(input_ooi: X509Certificate, config: Config | None) -> Iterator[OOI]:
    threshold_very_soon = datetime.timedelta(
        days=config.config.get("expiring-very-soon-in-days", 15) if config and config.config else 15
    )
    threshold_soon = datetime.timedelta(
        days=config.config.get("expiring-soon-in-days", 30) if config and config.config else 30
    )

    # only applies to OOIs referencing the certificate
    if input_ooi.expired:
        ft = KATFindingType(id="KAT-CERTIFICATE-EXPIRED")
        yield ft
        yield Finding(ooi=input_ooi.reference, finding_type=ft.reference, description="TLS certificate has expired")

    elif input_ooi.expires_in is not None and input_ooi.expires_in < threshold_very_soon:
        ft = KATFindingType(id="KAT-CERTIFICATE-EXPIRING-VERY-SOON")
        yield ft
        yield Finding(
            ooi=input_ooi.reference, finding_type=ft.reference, description="TLS certificate is expiring very soon"
        )
    elif input_ooi.expires_in is not None and input_ooi.expires_in < threshold_soon:
        ft = KATFindingType(id="KAT-CERTIFICATE-EXPIRING-SOON")
        yield ft
        yield Finding(
            ooi=input_ooi.reference, finding_type=ft.reference, description="TLS certificate is expiring soon"
        )
