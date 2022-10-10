import ipaddress
import json
from typing import Iterator, Union

from octopoes.models import OOI, Reference
from octopoes.models.ooi.certificate import Certificate
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.network import (
    IPPort,
    Protocol,
    PortState,
    IPAddressV4,
    IPAddressV6,
    Network,
)
from octopoes.models.ooi.software import Software, SoftwareInstance
from boefjes.job import NormalizerMeta


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterator[OOI]:
    results = json.loads(raw)
    ooi = Reference.from_str(normalizer_meta.boefje_meta.input_ooi)

    network = Network(name="internet").reference
    ip = results["ip"]
    ipvx = ipaddress.ip_address(ip)
    if ipvx.version == 4:
        ip_ooi = IPAddressV4(
            address=ip,
            network=network,
        )
    else:
        ip_ooi = IPAddressV6(
            address=ip,
            network=network,
        )

    if 'dns' in results.keys() and 'names' in results["dns"].keys():
        for hostname in results["dns"]["names"]:
            hostname_ooi = Hostname(name=hostname, network=network)
            yield hostname_ooi

    for scan in results["services"]:
        port_nr = scan["port"]
        transport = scan["transport_protocol"].lower()

        ip_port = IPPort(
            address=ooi,
            protocol=Protocol(transport),
            port=int(port_nr),
            state=PortState("open"),
        )
        yield ip_port

        if 'tls' in scan.keys():
            certificate = scan["tls"]["certificates"]
            if 'subject_dn' in certificate["leaf_data"]:
                cert_subject=certificate["leaf_data"]["subject_dn"]
            elif 'subject' in certificate["leaf_data"]:
                so=certificate["leaf_data"]["subject_dn"]
                cert_subject="C={}, ST={}, O={}, OU={}, CN={}".format(
                    so["country"],so["province"],so["organization"],so["organizational_unit"],so["common_name"])
            else:
                cert_subject="n/a"
            yield Certificate(
                subject=cert_subject,
                issuer=certificate["leaf_data"]["issuer_dn"],
                valid_from=0,
                valid_until=0,
                pk_algorithm=certificate["leaf_data"]["pubkey_algorithm"],
                pk_size=certificate["leaf_data"]["pubkey_bit_size"],
                pk_number=certificate["leaf_data"]["fingerprint"],
                website="",
                signed_by=None
            )

        if 'software' in scan.keys():
            for sw in scan["software"]:
                if "version" in sw.keys():
                    software_ooi = Software(name=sw["product"].upper(), version=sw["version"])
                else:
                    software_ooi = Software(name=sw["product"].upper())

                yield software_ooi
                yield SoftwareInstance(
                    ooi=ip_port.reference, software=software_ooi.reference
                )

