from typing import List, Iterator, Union

from octopoes.models import OOI
from octopoes.models.ooi.dns.zone import ResolvedHostname
from octopoes.models.ooi.findings import KATFindingType, Finding
from octopoes.models.ooi.web import HTTPResource, HTTPHeader


def run(
    resource: HTTPResource,
    additional_oois: List[Union[HTTPHeader, ResolvedHostname]],
) -> Iterator[OOI]:

    if not additional_oois:
        return

    header_keys = [header.key.lower() for header in additional_oois]

    if "location" in header_keys:
        return

    if "strict-transport-security" not in header_keys:
        ft = KATFindingType(id="KAT-500")
        yield ft
        finding = Finding(
            finding_type=ft.reference,
            ooi=resource.reference,
            description="Header strict-transport-security is missing or not configured correctly.",
        )
        yield finding

    if "content-security-policy" not in header_keys:
        ft = KATFindingType(id="KAT-501")
        finding = Finding(
            finding_type=ft.reference,
            ooi=resource.reference,
            description="Header content-security-policy is missing or not configured correctly.",
        )
        yield ft
        yield finding

    if "x-permitted-cross-domain-policies" not in header_keys:
        ft = KATFindingType(id="KAT-502")
        finding = Finding(
            finding_type=ft.reference,
            ooi=resource.reference,
            description="Header x-permitted-cross-domain-policies is missing or not configured correctly.",
        )
        yield ft
        yield finding

    if "x-xss-protection" not in header_keys:
        ft = KATFindingType(id="KAT-503")
        finding = Finding(
            finding_type=ft.reference,
            ooi=resource.reference,
            description="Header x-xss-protection is missing or not configured correctly.",
        )
        yield ft
        yield finding

    if "x-frame-options" not in header_keys:
        ft = KATFindingType(id="KAT-504")
        finding = Finding(
            finding_type=ft.reference,
            ooi=resource.reference,
            description="Header x-frame-options is missing or not configured correctly.",
        )
        yield ft
        yield finding

    if "x-dns-prefetch-control" not in header_keys:
        ft = KATFindingType(id="KAT-505")
        finding = Finding(
            finding_type=ft.reference,
            ooi=resource.reference,
            description="Header x-dns-prefetch-control is missing or not configured correctly.",
        )
        yield ft
        yield finding

    if "expect-ct" not in header_keys:
        ft = KATFindingType(id="KAT-506")
        finding = Finding(
            finding_type=ft.reference,
            ooi=resource.reference,
            description="Header expect-ct is missing or not configured correctly.",
        )
        yield ft
        yield finding

    if "permissions-policy" not in header_keys:
        ft = KATFindingType(id="KAT-507")
        finding = Finding(
            finding_type=ft.reference,
            ooi=resource.reference,
            description="Header permissions-policy is missing or not configured correctly.",
        )
        yield ft
        yield finding

    if "referrer-policy" not in header_keys:
        ft = KATFindingType(id="KAT-508")
        finding = Finding(
            finding_type=ft.reference,
            ooi=resource.reference,
            description="Header referrer-policy is missing or not configured correctly.",
        )
        yield ft
        yield finding

    if "x-content-type-options" not in header_keys:
        ft = KATFindingType(id="KAT-509")
        finding = Finding(
            finding_type=ft.reference,
            ooi=resource.reference,
            description="Header x-content-type-options is missing or not configured correctly.",
        )
        yield ft
        yield finding
