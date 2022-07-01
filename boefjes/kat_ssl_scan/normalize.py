import xml.etree.ElementTree as ET
from typing import Union, Iterator

from octopoes.models import OOI, Reference
from octopoes.models.ooi.findings import KATFindingType, Finding

from job import NormalizerMeta


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterator[OOI]:
    root = ET.fromstring(raw)
    website_reference = Reference.from_str(normalizer_meta.boefje_meta.input_ooi)

    protocols = []
    for protocol in root.findall("./ssltest/protocol"):
        type_ = protocol.attrib["type"]
        version = protocol.attrib["version"]
        enabled = protocol.attrib["enabled"] == "1"

        protocols.append((type_, version, enabled))

    test = root.find("./ssltest")

    if ("ssl", "2", True) in protocols:
        kft = KATFindingType(id="KAT-540")
        yield kft
        yield Finding(finding_type=kft.reference, ooi=website_reference)
    elif ("ssl", "3", True) in protocols:
        kft = KATFindingType(id="KAT-541")
        yield kft
        yield Finding(finding_type=kft.reference, ooi=website_reference)
    elif ("tls", "1.0", True) in protocols and ("tls", "1.1", False) in protocols:
        kft = KATFindingType(id="KAT-542")
        yield kft
        yield Finding(finding_type=kft.reference, ooi=website_reference)
    elif ("tls", "1.1", True) in protocols and ("tls", "1.0", False) in protocols:
        kft = KATFindingType(id="KAT-543")
        yield kft
        yield Finding(finding_type=kft.reference, ooi=website_reference)
    elif ("tls", "1.0", True) in protocols and ("tls", "1.1", True) in protocols:
        kft = KATFindingType(id="KAT-544")
        yield kft
        yield Finding(finding_type=kft.reference, ooi=website_reference)
    elif ("tls", "1.2", False) in protocols:
        kft = KATFindingType(id="KAT-545")
        yield kft
        yield Finding(finding_type=kft.reference, ooi=website_reference)
    elif ("tls", "1.3", False) in protocols:
        kft = KATFindingType(id="KAT-546")
        yield kft
        yield Finding(finding_type=kft.reference, ooi=website_reference)

    fallback = root.find("./ssltest/fallback")
    if fallback is not None and fallback.attrib["supported"] != "1":
        kft = KATFindingType(id="KAT-547")
        yield kft
        yield Finding(finding_type=kft.reference, ooi=website_reference)
