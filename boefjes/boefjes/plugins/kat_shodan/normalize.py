import json
import logging
from typing import Iterable, Union

from boefjes.job_models import NormalizerMeta
from octopoes.models import OOI, Reference
from octopoes.models.ooi.findings import CVEFindingType, Finding
from octopoes.models.ooi.network import IPPort, PortState, Protocol


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterable[OOI]:
    results = json.loads(raw)
    ooi = Reference.from_str(normalizer_meta.raw_data.boefje_meta.input_ooi)

    if not results:
        logging.info("No Shodan results available for normalization.")
    elif "data" not in results:
        logging.warning("Shodan results exist without data.")
    else:
        for scan in results["data"]:
            port_nr = scan["port"]
            transport = scan["transport"]

            ip_port = IPPort(
                address=ooi,
                protocol=Protocol(transport),
                port=int(port_nr),
                state=PortState("open"),
            )
            yield ip_port

            if "vulns" in scan:
                for cve, _ in scan["vulns"].items():
                    ft = CVEFindingType(id=cve)
                    f = Finding(finding_type=ft.reference, ooi=ip_port.reference)
                    yield ft
                    yield f
