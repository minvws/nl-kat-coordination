import ipaddress
import json
from typing import Iterator, Union

from octopoes.models import OOI, Reference
from octopoes.models.ooi.network import (
    IPPort,
    Protocol,
    PortState,
    IPAddressV4,
    IPAddressV6,
    Network,
)
from octopoes.models.ooi.software import Software, SoftwareInstance

from job import NormalizerMeta


def get_name_from_cpe(cpe: str) -> str:
    splitted = []
    if cpe[0:5] == "cpe:/":
        splitted = cpe[5:].split(":")
    elif cpe[0:8] == "cpe:2.3:":
        splitted = cpe[8:].split(":")

    if len(splitted) > 3:
        return splitted[2]
    else:
        return cpe


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterator[OOI]:
    results = json.loads(raw)
    boefje_meta = normalizer_meta.boefje_meta
    input_ = boefje_meta.arguments["input"]
    pk_ooi = Reference.from_str(boefje_meta.input_ooi)
    network = Network(name="internet").reference

    # Structure based on https://docs.binaryedge.io/modules/<accepted_modules_name>/
    accepted_modules = ("ssh", "rsync", "ftp", "telnet", "smb")
    for scan in results["results"]:
        module = scan["origin"]["type"]
        if module not in accepted_modules:
            continue

        port_nr = int(scan["target"]["port"])
        protocol = scan["target"]["protocol"]
        ip = scan["target"]["ip"]

        if input_["ooi_type"] in ["IPAddressV4", "IPAddressV6"]:
            ip_ref = pk_ooi
        else:
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
            yield ip_ooi
            ip_ref = ip_ooi.reference

        ip_port_ooi = IPPort(
            address=ip_ref,
            protocol=Protocol(protocol),
            port=port_nr,
            state=PortState("open"),
        )
        yield ip_port_ooi

        if module == "ssh":
            version_ssh = scan.get("result", {}).get("data", {}).get("banner")
            if version_ssh:
                software_ooi = Software(name=module.upper(), version=version_ssh)
            else:
                software_ooi = Software(name=module.upper())
            yield software_ooi
            yield SoftwareInstance(
                ooi=ip_port_ooi.reference, software=software_ooi.reference
            )
        elif module == "rsync":
            software_ooi = Software(
                name=module.upper(),
                version=scan.get("result", {}).get("data", {}).get("version"),
            )
            yield software_ooi
            yield SoftwareInstance(
                ooi=ip_port_ooi.reference, software=software_ooi.reference
            )
        elif module == "telnet":
            software_ooi = Software(name=module.upper())
            yield software_ooi
            yield SoftwareInstance(
                ooi=ip_port_ooi.reference, software=software_ooi.reference
            )
        elif module == "smb":
            for dialect in (
                scan.get("result", {}).get("data", {}).get("smb_dialects", [])
            ):
                software_ooi = Software(name=module.upper(), version=dialect)
                yield software_ooi
                yield SoftwareInstance(
                    ooi=ip_port_ooi.reference, software=software_ooi.reference
                )
            for cpe in scan.get("result", {}).get("data", {}).get("cpe", []):
                software_ooi = Software(name=get_name_from_cpe(cpe), cpe=cpe)
                yield software_ooi
                yield SoftwareInstance(
                    ooi=ip_port_ooi.reference, software=software_ooi.reference
                )

        # (potential) TODO: SSH: hassh, hassh-algoritms
        # (potential) TODO: RSYNC: result.data.status
        # (potential) TODO: RSYNC: result.data.modules[].status
