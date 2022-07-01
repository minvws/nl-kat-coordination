import json
from typing import Iterator, Union

from octopoes.models import OOI, Reference
from octopoes.models.ooi.findings import KATFindingType, Finding
from octopoes.models.ooi.network import IPPort, Protocol, PortState
from octopoes.models.ooi.software import Software, SoftwareInstance

from job import NormalizerMeta


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterator[OOI]:
    results = json.loads(raw)
    boefje_meta = normalizer_meta.boefje_meta
    ooi = Reference.from_str(boefje_meta.input_ooi)

    for port in results["open_ports"]:
        ip_port_ooi = IPPort(
            address=ooi,
            protocol=Protocol("tcp"),
            port=int(port),
            state=PortState("open"),
        )
        yield ip_port_ooi

        software_ooi = Software(name="DICOM")
        yield software_ooi
        software_instance_ooi = SoftwareInstance(
            ooi=ip_port_ooi.reference, software=software_ooi.reference
        )
        yield software_instance_ooi

        kat_ooi = KATFindingType(id="KAT-643")
        yield kat_ooi
        yield Finding(
            finding_type=kat_ooi.reference,
            ooi=software_instance_ooi.reference,
            description=f"A DICOM (Digital Imaging and Communications in Medicine) server is exposed to the internet.",
        )
