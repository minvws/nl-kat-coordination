from typing import Iterable, List, Tuple, Union

from boefjes.job_models import NormalizerMeta
from octopoes.models import OOI, Reference
from octopoes.models.ooi.findings import CVEFindingType, Finding
from octopoes.models.ooi.software import Software, SoftwareInstance
from packaging import version

VULNERABLE_RANGES: List[Tuple[str, str]] = [("0", "11.8.1.1"), ("11.9.0.0", "11.9.1.1"), ("11.10.0.0", "11.10.0.2")]


def extract_js_version(html_content: str) -> Union[version.Version, bool]:
    telltale = "/mifs/scripts/auth.js?"
    telltale_position = html_content.find(telltale)
    if telltale_position == -1:
        return False
    version_end = html_content.find('"', telltale_position)
    version_string = html_content[telltale_position + len(telltale) : version_end]
    if not version_string:
        return False
    return version.parse(" ".join(strip_vsp_and_build(version_string)))


def extract_css_version(html_content: str) -> Union[version.Version, bool]:
    telltale = "/mifs/css/windowsAllAuth.css?"
    telltale_position = html_content.find(telltale)
    if telltale_position == -1:
        return False
    version_end = html_content.find('"', telltale_position)
    version_string = html_content[telltale_position + len(telltale) : version_end]
    if not version_string:
        return False
    return version.parse(" ".join(strip_vsp_and_build(version_string)))


def strip_vsp_and_build(url: str) -> Iterable[str]:
    url_parts = url.split()
    for part in url_parts:
        if str(part).lower() == "vsp":
            continue
        if str(part).lower() == "build":
            break
        yield part


def are_vulnerable_versions(
    vulnerable_ranges: List[Tuple[version.Version, version.Version]], detected_versions: List[version.Version]
) -> bool:
    for detected_version in detected_versions:
        for start, end in vulnerable_ranges:
            if start <= detected_version < end:
                return True
    return False


def run(normalizer_meta: NormalizerMeta, raw: bytes) -> Iterable[OOI]:
    ooi = Reference.from_str(normalizer_meta.raw_data.boefje_meta.input_ooi)
    html = raw.decode()
    detected_versions = [extract_js_version(html), extract_css_version(html)]
    if not any(detected_versions):
        return

    software = Software(name="Ivanti EPMM", version=str(detected_versions[0]))
    software_instance = SoftwareInstance(ooi=ooi, software=software.reference)
    yield software
    yield software_instance
    vulnerable = are_vulnerable_versions(
        [(version.parse(start), version.parse(end)) for start, end in VULNERABLE_RANGES], detected_versions
    )
    if vulnerable:
        finding_type = CVEFindingType(id="CVE-2023-35078")
        finding = Finding(
            finding_type=finding_type.reference,
            ooi=software_instance.reference,
            description="Software is most likely vulnerable to CVE-2023-35078",
        )
        yield finding_type
        yield finding
