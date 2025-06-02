import json
from collections.abc import Iterable

import structlog

from octopoes.models import OOI, Reference
from octopoes.models.ooi.findings import Finding, KATFindingType

logger = structlog.get_logger(__name__)


def run(input_ooi: dict[str, str], raw: bytes) -> Iterable[OOI]:
    """Normalize witha.name output."""
    result = json.loads(raw)

    if result["targets"] is None:
        logger.info("No targets found in witha.name output")
        return

    input_ooi_reference = Reference.from_str(input_ooi["primary_key"])
    found_targets = None

    ooi_category = "Hostname" if input_ooi["object_type"] == "Hostname" else "IP"

    if ooi_category == "IP":
        logger.debug("Found IP address: %s", input_ooi["primary_key"])
        found_targets = [
            target for target in result["targets"] if target["ip"] == input_ooi_reference.tokenized.address
        ]
    else:
        logger.debug("Found Hostname address: %s", input_ooi["primary_key"])
        # Make host always start with www.
        raw_host = input_ooi["name"].lower()
        host = raw_host if raw_host.startswith("www.") else "www." + raw_host

        # Because hosts are listed with and without www. prefix, we need to check both
        found_targets = [target for target in result["targets"] if target["host"] in [host, host.removeprefix("www.")]]

    logger.info("Found targets: %s", found_targets)
    if not found_targets:
        logger.info("No targets found for %s", input_ooi["primary_key"])
        return

    # For all listed ports, and attacks construct a single finding
    report_data = [
        {
            "port": target["port"] or "an unknown",
            "type": target["type"] or "an unknown",
            "method": target["method"] or "an unknown",
            "path": target["path"] or "/",
        }
        for target in found_targets
    ]

    description = (
        f"{ooi_category} {input_ooi_reference.human_readable} is listed for targeting by DDoSia,"
        + " and".join(
            [
                f" on port {data['port']}, over {data['type']} using {data['method']} method on {data['path']}"
                for data in report_data
            ]
        )
    )

    ft = KATFindingType(id="KAT-DDOS-TARGET-DETECTED")

    finding = Finding(finding_type=ft.reference, ooi=input_ooi_reference, description=description)

    yield ft
    yield finding
