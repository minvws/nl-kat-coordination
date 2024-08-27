import json
import logging
from collections.abc import Iterable

from boefjes.job_models import NormalizerOutput
from octopoes.models import Reference
from octopoes.models.ooi.findings import Finding, KATFindingType
from octopoes.models.ooi.software import Software, SoftwareInstance


def scan_outdated_software(data: dict, ooi_ref):
    for scan in data:
        for vulnerability in scan["vulnerabilities"]:
            # If the scanned vulnerability has to do with outdated software
            if vulnerability["id"].startswith("6"):
                # Example of `vulnerability["msg"]`
                # @SOFTWARE/@RUNNING_VER appears to be outdated (current is at least @CURRENT_VER)
                software_name, found_version = vulnerability["msg"].split()[0].split("/")

                software = Software(name=software_name, version=found_version)
                software_instance = SoftwareInstance(ooi=ooi_ref, software=software.reference)
                yield software
                yield software_instance

                finding_type = KATFindingType(id="KAT-VERIFIED-VULNERABILITY")
                yield finding_type
                yield Finding(
                    finding_type=finding_type.reference,
                    ooi=software_instance.reference,
                    description=vulnerability["msg"],
                )


def run(input_ooi: dict, raw: bytes) -> Iterable[NormalizerOutput]:
    logging.info(input_ooi)
    data = json.loads(raw)

    ooi_ref = Reference.from_str(input_ooi["primary_key"])

    yield from scan_outdated_software(data, ooi_ref)
