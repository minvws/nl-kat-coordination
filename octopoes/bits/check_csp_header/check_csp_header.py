import ipaddress
import re
from typing import Dict, Iterator, List

from octopoes.models import OOI, Reference
from octopoes.models.ooi.findings import Finding, KATFindingType
from octopoes.models.types import HTTPHeader

NON_DECIMAL_FILTER = re.compile(r"[^\d.]+")


def run(input_ooi: HTTPHeader, additional_oois: List, config: Dict[str, str]) -> Iterator[OOI]:
    header = input_ooi
    if header.key.lower() != "content-security-policy":
        return

    findings: [str] = []

    if "http://" in header.value:
        findings.append("Http should not be used in the CSP settings of an HTTP Header.")

    # checks for a wildcard in domains in the header
    # 1: one or more non-whitespace
    # 2: wildcard
    # 3: second-level domain
    # 4: end with either a space, a ';', a :port or the end of the string
    #              {1}{ 2}{  3  }{         4       }
    if re.search(r"\S+\*\.\S{2,3}([\s]+|$|;|:[0-9]+)", header.value):
        findings.append("The wildcard * for the scheme and host part of any URL should never be used in CSP settings.")

    if "unsafe-inline" in header.value or "unsafe-eval" in header.value or "unsafe-hashes" in header.value:
        findings.append(
            "Unsafe-inline, unsafe-eval and unsafe-hashes should not be used in the CSP settings of an HTTP Header."
        )

    if "frame-src" not in header.value and "default-src" not in header.value and "child-src" not in header.value:
        findings.append("Frame-src has not been defined or does not have a fallback.")

    if "script-src" not in header.value and "default-src" not in header.value:
        findings.append("Script-src has not been defined or does not have a fallback.")

    if "frame-ancestors" not in header.value:
        findings.append("Frame-ancestors has not been defined.")

    if "default-src" not in header.value:
        findings.append("Default-src has not been defined.")

    policies = [policy.strip().split(" ") for policy in header.value.split(";")]
    for policy in policies:
        if policy[0] in ["frame-src", "frame-ancestors"] and not _source_valid(policy[1:]):
            findings.append(f"{policy[0]} has not been correctly defined.")

        if policy[0] == "default-src" and (
            ("'none'" not in policy and "'self'" not in policy) or not _source_valid(policy[2:])
        ):
            findings.append(f"{policy[0]} has not been correctly defined.")

        if (policy[0] == "default-src" or policy[0] == "object-src" or policy[0] == "script-src") and "data:" in policy:
            findings.append(
                "'Data:' should not be used in the value of default-src, object-src and script-src in the CSP settings."
            )
        if policy[1].strip() == "*":
            findings.append("A wildcard source should not be used in the value of any type in the CSP settings.")
        if policy[1].strip() in ("http:", "https:"):
            findings.append(
                "a blanket protocol source should not be used in the value of any type in the CSP settings."
            )
        for source in policy[1:]:
            if not _ip_valid(source):
                findings.append(
                    "Private, local, reserved, multicast, loopback ips should not be allowed in the CSP settings."
                )
    if findings:
        description: str = "List of CSP findings:"
        for index, finding in enumerate(findings):
            description += f"\n {index + 1}. {finding}"

        yield from _create_kat_finding(
            header.reference,
            kat_id="KAT-CSP-VULNERABILITIES",
            description=description,
        )


def _ip_valid(source: str) -> bool:
    "Check if there are IP's in this source, return False if the address found was to be non global. Ignores non ips"
    ip = NON_DECIMAL_FILTER.sub("", source)
    if ip:
        try:
            ip = ipaddress.ip_address(ip)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved:
                return False
        except ValueError:
            pass
    return True


def _create_kat_finding(header: Reference, kat_id: str, description: str) -> Iterator[OOI]:
    finding_type = KATFindingType(id=kat_id)
    yield finding_type
    yield Finding(
        finding_type=finding_type.reference,
        ooi=header,
        description=description,
    )


def _source_valid(policy: [str]) -> bool:
    for value in policy:
        if not (
            re.search(r"\S+\.\S{2,3}([\s]+|$|;|:[0-9]+)", value)
            or value
            in [
                "'none'",
                "'self'",
                "data:",
                "unsafe-inline",
                "unsafe-eval",
                "unsafe-hashes",
                "report-sample",
            ]
        ):
            return False

    return True
