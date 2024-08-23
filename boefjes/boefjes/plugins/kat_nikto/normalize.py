import json
import logging
import re
from collections.abc import Iterable

from boefjes.job_models import NormalizerOutput
from octopoes.models import Reference
from octopoes.models.ooi.software import OutdatedSoftwareInstance, Software, SoftwareInstance


def scan_outdated_software(data: dict, ooi_ref):
    for scan in data:
        for vulnerability in scan["vulnerabilities"]:
            # If the scanned vulnerability has to do with outdated software
            if vulnerability["id"].startswith("6"):
                software_name, found_version = vulnerability["msg"].split()[0].split("/")

                # REGEX: get the text between "least " and ")" to get the latest version
                match = re.search(r"least (.*)\)", vulnerability["msg"])
                if match is None:
                    logging.error("No version number found on supposedly outdated software")
                    continue
                newest_version = match.group(1)
                software = Software(name=software_name, version=found_version)
                software_instance = SoftwareInstance(ooi=ooi_ref, software=software.reference)
                yield software
                yield software_instance
                yield OutdatedSoftwareInstance(
                    ooi=ooi_ref,
                    software_instance=software_instance.reference,
                    newest_version=newest_version,
                )


def run(input_ooi: dict, raw: bytes) -> Iterable[NormalizerOutput]:
    logging.info(input_ooi)
    data = json.loads(raw)

    ooi_ref = Reference.from_str(input_ooi["primary_key"])

    yield from scan_outdated_software(data, ooi_ref)
