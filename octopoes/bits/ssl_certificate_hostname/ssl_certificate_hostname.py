from typing import List, Iterator, Union

from octopoes.models import OOI
from octopoes.models.ooi.certificate import (
    X509Certificate,
    SubjectAlternativeNameHostname,
    SubjectAlternativeNameQualifier,
)
from octopoes.models.ooi.findings import KATFindingType, Finding
from octopoes.models.ooi.web import Website


def is_part_of_wildcard(hostname: str, wildcard: str) -> bool:
    # according to rfc2459 wildcard certificates can only be used for subdomains
    wildcard_domain = wildcard[2:].rstrip(".")
    higher_level_domain = ".".join(hostname.split(".")[1:])
    return wildcard_domain == higher_level_domain


def subject_valid_for_hostname(subject: str, hostname: str) -> bool:
    if subject == hostname:
        return True
    if subject.startswith("*"):
        return is_part_of_wildcard(hostname, subject)
    return False


def hostname_in_qualifiers(hostname: str, qualifiers: List[str]) -> bool:
    for qualifier in qualifiers:
        if is_part_of_wildcard(hostname, qualifier):
            return True
    return False


def run(
    input_ooi: X509Certificate,
    additional_oois: List[Union[Website, SubjectAlternativeNameHostname]],
) -> Iterator[OOI]:
    subject = input_ooi.subject.rstrip(".")

    websites = [website for website in additional_oois if isinstance(website, Website)]
    subject_alternative_name_hostnames = [
        subject_alternative_name.hostname.tokenized.name.rstrip(".")
        for subject_alternative_name in additional_oois
        if isinstance(subject_alternative_name, SubjectAlternativeNameHostname)
    ]

    subject_alternative_name_qualifiers = [
        subject_alternative_name.name.rstrip(".")
        for subject_alternative_name in additional_oois
        if isinstance(subject_alternative_name, SubjectAlternativeNameQualifier)
    ]

    for website in websites:
        hostname = website.hostname.tokenized.name.rstrip(".")

        if subject_valid_for_hostname(subject, hostname):
            return

        if hostname in subject_alternative_name_hostnames:
            return

        if hostname_in_qualifiers(hostname, subject_alternative_name_qualifiers):
            return

        ft = KATFindingType(id="KAT-SSL-CERT-HOSTNAME-MISMATCH")
        yield Finding(
            ooi=website.reference,
            finding_type=ft.reference,
            description=f"The hostname {website.hostname} does not match the subject of the certificate",
        )
