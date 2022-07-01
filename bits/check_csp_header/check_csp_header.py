import re
from typing import List, Iterator

from octopoes.models import OOI, Reference
from octopoes.models.ooi.findings import KATFindingType, Finding
from octopoes.models.types import HTTPHeader


def run(
    input_ooi: HTTPHeader,
    additional_oois: List,
) -> Iterator[OOI]:

    header = input_ooi
    if header.key.lower() != "content-security-policy":
        return

    findings: [str] = []

    if "http://" in header.value:
        findings.append("Http should not be used in the CSP settings of an HTTP Header.")

    if "127.0.0.1" in header.value:
        findings.append("127.0.0.1 should not be used in the CSP settings of an HTTP Header.")

    # checks for a wildcard in domains in the header
    # one or more non-whitespace, wildcard. (second-level domain), 2 or 3 non-whitespace characters (top-level domain), end with either a space, a ';', a :port or the end of the string
    # \S+                         \*\.                             \S{2,3}                                              ([\s]+|$|;)
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

        if policy[0] in ["frame-src", "frame-ancestors"]:
            if not _source_valid(policy[1:]):
                findings.append(f"{policy[0]} has not been correctly defined.")

        if policy[0] == "default-src":
            if ("'none'" not in policy and "'self'" not in policy) or not _source_valid(policy[2:]):
                findings.append(f"{policy[0]} has not been correctly defined.")

        if (policy[0] == "default-src" or policy[0] == "object-src" or policy[0] == "script-src") and "data:" in policy:
            findings.append(
                "'Data:' should not be used in the value of default-src, object-src and script-src in the CSP settings."
            )

    if findings:
        description: str = "List of CSP findings:"
        for index, finding in enumerate(findings):
            description += f"\n {index + 1}. {finding}"

        yield from _create_kat_finding(
            header.reference,
            kat_id="KAT-607",
            description=description,
        )


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
