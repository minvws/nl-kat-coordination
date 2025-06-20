from collections.abc import Iterator

from octopoes.models import OOI
from octopoes.models.ooi.dns.zone import ResolvedHostname
from octopoes.models.ooi.service import IPService
from octopoes.models.ooi.web import Website


def nibble(resolved_hostname: ResolvedHostname, ip_service: IPService) -> Iterator[OOI]:
    yield Website(hostname=resolved_hostname.hostname, ip_service=ip_service.reference)
