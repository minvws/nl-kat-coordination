import json
import logging
from collections.abc import Iterable

from octopoes.models import OOI, Reference
from octopoes.models.ooi.findings import Finding, KATFindingType


def run(input_ooi: dict, raw: bytes) -> Iterable[OOI]:
    """Normalize witha.name output."""
    result = json.loads(raw)
    input_ooi_reference = Reference.from_str(input_ooi["primary_key"])

    if input_ooi["primary_key"].startswith("IPAddress"):
        address = input_ooi_reference.tokenized.address
        host = None
    else:
        host = input_ooi["name"].lower().strip().lstrip("*.").rstrip(".")
        address = None

    ft = None
    if not result:
        logging.info("No witha.name results available for normalization.")
    elif "targets" in result:
        listings = {}
        for report in result.get("targets", []):
            if (
                (
                    host
                    and (report.get("host", "").lower() == host)
                    or report.get("host", "").lstrip("*.").lower() == host
                )
                or address
                and report.get("address", "") == address
            ):
                if result["target_id"] not in listings:
                    listings[result["target_id"]] = [
                        (
                            f"IP {input_ooi_reference.human_readable}"
                            if address
                            else f"Hostname {input_ooi_reference.human_readable}ytho is listed for tagetting by Ddosia."
                        )
                    ]
                listings[result["target_id"]].extend(
                    [
                        report.get("type", "unknown protocol"),
                        report.get("method", "unknown method"),
                        report.get("port", "unknown port"),
                        report.get("path", "unknown path"),
                    ]
                )
        if not ft:
            ft = KATFindingType("KAT-DDOS-TARGET-DETECTED")
        # for all listed ports, and attacks construct a single finding
        description = [
            listing[0]
            + " and ".join(list(map(lambda x: f" on port {x[2]}, over {x[0]} using {x[1]} on {x[3]}", listing[1:])))
            for target_id, listing in listings.items()
        ]
        finding = Finding(finding_type=ft.reference, ooi=input_ooi_reference, description=description)
        yield ft
        yield finding
