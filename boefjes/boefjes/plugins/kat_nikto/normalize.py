import json
import logging
from collections.abc import Iterable

from boefjes.job_models import NormalizerOutput
from octopoes.models import Reference
from octopoes.models.ooi.software import Software, SoftwareInstance


def scan_outdated_software(data: dict, ooi_ref):
    for scan in data:
        for vulnerability in scan["vulnerabilities"]:
            # If the scanned vulnerability has to do with outdated software
            if vulnerability["id"].startswith("6"):
                software_name, found_version = vulnerability["msg"].split()[0].split("/")

                software = Software(name=software_name, version=found_version)
                yield software
                yield SoftwareInstance(ooi=ooi_ref, software=software.reference)


def run(input_ooi: dict, raw: bytes) -> Iterable[NormalizerOutput]:
    logging.info(input_ooi)
    data = json.loads(raw)

    ooi_ref = Reference.from_str(input_ooi["primary_key"])

    yield from scan_outdated_software(data, ooi_ref)
