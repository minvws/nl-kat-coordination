from typing import Dict, Iterator, List

from octopoes.models import OOI
from octopoes.models.ooi.findings import Finding, KATFindingType
from octopoes.models.ooi.web import HTTPHeader, HTTPResource


def run(resource: HTTPResource, additional_oois: List[HTTPHeader], config: Dict[str, str]) -> Iterator[OOI]:
    if not additional_oois:
        return

    header_keys = [header.key.lower() for header in additional_oois]

    if "location" in header_keys:
        return

    if "strict-transport-security" not in header_keys and resource.reference.tokenized.web_url.scheme != "http":
        ft = KATFindingType(id="KAT-NO-HSTS")
        yield ft
        finding = Finding(
            finding_type=ft.reference,
            ooi=resource.reference,
            description="Header strict-transport-security is missing or not configured correctly.",
        )
        yield finding

    if "content-security-policy" not in header_keys:
        ft = KATFindingType(id="KAT-NO-CSP")
        finding = Finding(
            finding_type=ft.reference,
            ooi=resource.reference,
            description="Header content-security-policy is missing or not configured correctly.",
        )
        yield ft
        yield finding

    if "x-permitted-cross-domain-policies" not in header_keys:
        ft = KATFindingType(id="KAT-NO-X-PERMITTED-CROSS-DOMAIN-POLICIES")
        finding = Finding(
            finding_type=ft.reference,
            ooi=resource.reference,
            description="Header x-permitted-cross-domain-policies is missing or not configured correctly.",
        )
        yield ft
        yield finding

    if "x-xss-protection" not in header_keys:
        ft = KATFindingType(id="KAT-NO-EXPLICIT-XSS-PROTECTION")
        finding = Finding(
            finding_type=ft.reference,
            ooi=resource.reference,
            description="Header x-xss-protection is missing or not configured correctly.",
        )
        yield ft
        yield finding

    if "x-frame-options" not in header_keys:
        ft = KATFindingType(id="KAT-NO-X-FRAME-OPTIONS")
        finding = Finding(
            finding_type=ft.reference,
            ooi=resource.reference,
            description="Header x-frame-options is missing or not configured correctly.",
        )
        yield ft
        yield finding

    if "x-dns-prefetch-control" not in header_keys:
        ft = KATFindingType(id="KAT-NO-X-DNS-PREFETCH-CONTROL")
        finding = Finding(
            finding_type=ft.reference,
            ooi=resource.reference,
            description="Header x-dns-prefetch-control is missing or not configured correctly.",
        )
        yield ft
        yield finding

    if "permissions-policy" not in header_keys:
        ft = KATFindingType(id="KAT-NO-PERMISSIONS-POLICY")
        finding = Finding(
            finding_type=ft.reference,
            ooi=resource.reference,
            description="Header permissions-policy is missing or not configured correctly.",
        )
        yield ft
        yield finding

    if "referrer-policy" not in header_keys:
        ft = KATFindingType(id="KAT-NO-REFERRER-POLICY")
        finding = Finding(
            finding_type=ft.reference,
            ooi=resource.reference,
            description="Header referrer-policy is missing or not configured correctly.",
        )
        yield ft
        yield finding

    if "x-content-type-options" not in header_keys:
        ft = KATFindingType(id="KAT-NO-X-CONTENT-TYPE-OPTIONS")
        finding = Finding(
            finding_type=ft.reference,
            ooi=resource.reference,
            description="Header x-content-type-options is missing or not configured correctly.",
        )
        yield ft
        yield finding
