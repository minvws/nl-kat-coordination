import ipaddress
import json
from collections.abc import Iterable
from urllib.parse import urlparse

from boefjes.job_models import NormalizerMeta
from octopoes.models import OOI, Reference
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.network import IPAddressV4, IPAddressV6, IPPort, Network
from octopoes.models.ooi.service import IPService, Service
from octopoes.models.ooi.web import URL, SecurityTXT, Website
from octopoes.models.types import Finding, KATFindingType


def run(normalizer_meta: NormalizerMeta, raw: bytes | str) -> Iterable[OOI]:
    results = json.loads(raw)
    boefje_meta = normalizer_meta.raw_data.boefje_meta
    website_original = Reference.from_str(boefje_meta.input_ooi)
    input_ = boefje_meta.arguments["input"]
    valid_results = []

    for path, details in results.items():
        # remove any nonsense locations from our validresults.
        if details["content"] is None or details.get("status", 200) != 200:
            continue
        valid_results[path] = details

        url_original = URL(
            raw=f'{input_["ip_service"]["service"]["name"]}://{input_["hostname"]["name"]}/{path}',
            network=Network(name=input_["hostname"]["network"]["name"]).reference,
        )
        yield url_original
        url = URL(raw=details["url"], network=Network(name=input_["hostname"]["network"]["name"]).reference)
        yield url

        url_parts = urlparse(details["url"])
        # we need to check if the website of the response is the same as the input website
        if (
            url_parts.scheme == input_["ip_service"]["service"]["name"]
            and url_parts.netloc == input_["hostname"]["name"]
            and details["ip"] == input_["ip_service"]["ip_port"]["address"]["address"]
        ):
            security_txt = SecurityTXT(
                website=website_original, url=url.reference, security_txt=details["content"], redirects_to=None
            )
            yield security_txt
        # otherwise we need to create a new website complete with hostname and ip
        else:
            hostname = Hostname(
                name=url_parts.netloc, network=Network(name=input_["hostname"]["network"]["name"]).reference
            )
            yield hostname
            addr = ipaddress.ip_address(details["ip"])
            if addr.version == 6:
                ip_address = IPAddressV6(
                    address=details["ip"], network=Network(name=input_["hostname"]["network"]["name"]).reference
                )
            else:
                ip_address = IPAddressV4(
                    address=details["ip"], network=Network(name=input_["hostname"]["network"]["name"]).reference
                )
            yield ip_address
            # check scheme for service and ipport
            if url_parts.scheme == "https":
                service = Service(name="https")
                yield service
                ip_port = IPPort(address=ip_address.reference, port=443, protocol="tcp")
                yield ip_port
                ip_service = IPService(ip_port=ip_port.reference, service=service.reference)
                yield ip_service
            else:
                service = Service(name="http")
                yield service
                ip_port = IPPort(address=ip_address.reference, port=80, protocol="tcp")
                yield ip_port
                ip_service = IPService(ip_port=ip_port.reference, service=service.reference)
                yield ip_service

            website = Website(hostname=hostname.reference, ip_service=ip_service.reference)
            yield website
            security_txt = SecurityTXT(
                website=website.reference, url=url.reference, security_txt=details["content"], redirects_to=None
            )
            yield security_txt
            # the original securitytxt redirects to this one
            security_txt_original = SecurityTXT(
                website=website_original,
                url=url_original.reference,
                redirects_to=security_txt.reference,
                security_txt=None,
            )
            yield security_txt_original

    # Check for legacy url https://www.rfc-editor.org/rfc/rfc9116#section-3-1
    if "security.txt" in valid_results and ".well-known/security.txt" not in valid_results:
        ft = KATFindingType(id="KAT-LEGACY-SECURITY-LOCATION")
        yield ft
        yield Finding(
            description="Only legacy /security.txt location found.", finding_type=ft.reference, ooi=website_original
        )
