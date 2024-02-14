import json
from collections.abc import Iterable

from boefjes.job_models import NormalizerMeta
from octopoes.models import OOI, Reference
from octopoes.models.ooi.findings import Finding, KATFindingType
from octopoes.models.ooi.network import IPPort, PortState, Protocol
from octopoes.models.ooi.software import Software, SoftwareInstance


def run(normalizer_meta: NormalizerMeta, raw: bytes | str) -> Iterable[OOI]:
    results = json.loads(raw)
    boefje_meta = normalizer_meta.raw_data.boefje_meta
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
        software_instance_ooi = SoftwareInstance(ooi=ip_port_ooi.reference, software=software_ooi.reference)
        yield software_instance_ooi

        kat_ooi = KATFindingType(id="KAT-DICOM-EXPOSED")
        yield kat_ooi
        yield Finding(
            finding_type=kat_ooi.reference,
            ooi=software_instance_ooi.reference,
            description="A DICOM (Digital Imaging and Communications in Medicine) server is exposed to the internet.",
        )
