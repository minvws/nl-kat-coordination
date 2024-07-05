"""
CVE-2024-6387 checker
Author: Mischa van Geelen <@rickgeex>

"""

from collections.abc import Iterable

from boefjes.job_models import NormalizerOutput
from octopoes.models import Reference
from octopoes.models.ooi.findings import CVEFindingType, Finding

VULNERABLE_VERSIONS = [
    "SSH-2.0-OpenSSH_8.5",
    "SSH-2.0-OpenSSH_8.6",
    "SSH-2.0-OpenSSH_8.7",
    "SSH-2.0-OpenSSH_8.8",
    "SSH-2.0-OpenSSH_8.9",
    "SSH-2.0-OpenSSH_9.0",
    "SSH-2.0-OpenSSH_9.1",
    "SSH-2.0-OpenSSH_9.2",
    "SSH-2.0-OpenSSH_9.3",
    "SSH-2.0-OpenSSH_9.4",
    "SSH-2.0-OpenSSH_9.5",
    "SSH-2.0-OpenSSH_9.6",
    "SSH-2.0-OpenSSH_9.7",
]

EXCLUDED_VERSIONS = [
    "SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.10",
    "SSH-2.0-OpenSSH_9.3p1 Ubuntu-3ubuntu3.6",
    "SSH-2.0-OpenSSH_9.6p1 Ubuntu-3ubuntu13.3",
    "SSH-2.0-OpenSSH_9.3p1 Ubuntu-1ubuntu3.6",
    "SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u3",
    "SSH-2.0-OpenSSH_8.4p1 Debian-5+deb11u3",
]


def run(input_ooi: dict, raw: bytes) -> Iterable[NormalizerOutput]:
    ooi = Reference.from_str(input_ooi["primary_key"])

    banner = raw.decode()

    if (
        "SSH-2.0-OpenSSH" in banner
        and any(version in banner for version in VULNERABLE_VERSIONS)
        and banner not in EXCLUDED_VERSIONS
    ):
        finding_type = CVEFindingType(id="CVE-2024-6387")
        finding = Finding(
            finding_type=finding_type.reference,
            ooi=ooi,
            description="Service is most likely vulnerable to CVE-2024-6387",
        )
        yield finding_type
        yield finding
