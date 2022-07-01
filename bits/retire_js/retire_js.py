import hashlib
import json
from os import path
from typing import List, Iterator, Dict, Union

from octopoes.models import OOI
from octopoes.models.ooi.findings import Finding, CVEFindingType, RetireJSFindingType
from octopoes.models.ooi.software import SoftwareInstance, Software
from packaging import version


def run(
    input_ooi: Software,
    additional_oois: List[SoftwareInstance],
) -> Iterator[OOI]:

    software_name = input_ooi.name
    software_version = input_ooi.version if input_ooi.version else "999.9.9"

    filename_path = path.join(path.dirname(__file__), "retirejs.json")
    with open(filename_path, encoding="utf-8") as json_file:
        known_vulnerabilities = json.load(json_file)

    vulnerabilities = _check_vulnerabilities(software_name, software_version, known_vulnerabilities)
    for vulnerability in vulnerabilities["CVE"]:
        for instance in additional_oois:
            ft = CVEFindingType(id=vulnerability)
            yield ft
            yield Finding(
                finding_type=ft.reference,
                ooi=instance.reference,
                description="This JavaScript Library has known vulnerabilities",
            )

    for vulnerability in vulnerabilities["RetireJS"]:
        for instance in additional_oois:
            ft = RetireJSFindingType(id=vulnerability)
            yield ft
            yield Finding(
                finding_type=ft.reference,
                ooi=instance.reference,
                description="This JavaScript Library has known vulnerabilities",
            )


def _check_vulnerabilities(name, package_version: str, known_vulnerabilities: Dict) -> Dict[str, List[str]]:
    vulnerabilities: Dict[str, List[str]] = {"CVE": [], "RetireJS": []}
    processed_name = _process_name(name)
    brand = [brand for brand in known_vulnerabilities if processed_name == _process_name(brand)][0]

    if brand:
        for known_vulnerability in known_vulnerabilities[brand]["vulnerabilities"]:
            if _check_versions(package_version, known_vulnerability):
                identifiers = known_vulnerability["identifiers"]
                if "CVE" in identifiers:
                    vulnerabilities["CVE"].append(identifiers["CVE"][0])
                else:
                    vulnerabilities["RetireJS"].append(f"RetireJS-{processed_name}-{_hash_identifiers(identifiers)}")

    return vulnerabilities


def _process_name(name: str) -> str:
    return name.lower().replace(" ", "").replace("_", "").replace("-", "").replace(".", "")


def _hash_identifiers(identifiers: Dict[str, Union[str, List[str]]]) -> str:
    pre_hash = ""
    for identifier in identifiers.values():
        pre_hash += "".join(identifier)
    return hashlib.sha1(pre_hash.encode()).hexdigest()[:4]


def _check_versions(package_version: str, known_vulnerability: dict) -> bool:
    below = version.parse(package_version) < version.parse(known_vulnerability["below"])
    # Some packages are only vulnerable below a version and not above
    above = (
        version.parse(package_version) >= version.parse(known_vulnerability["atOrAbove"])
        if "atOrAbove" in known_vulnerability
        else True
    )
    return below and above
