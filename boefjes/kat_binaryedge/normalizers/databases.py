import ipaddress
import json
from typing import Iterator, Union

from octopoes.models import OOI, Reference
from octopoes.models.ooi.findings import KATFindingType, Finding
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


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterator[OOI]:
    results = json.loads(raw)
    boefje_meta = normalizer_meta.boefje_meta
    input_ = boefje_meta.arguments["input"]
    pk_ooi = Reference.from_str(boefje_meta.input_ooi)
    network = Network(name="internet").reference

    # Structure based on https://docs.binaryedge.io/modules/<accepted_modules_name>/
    accepted_modules = (
        "cassandra",
        " elasticsearch",
        "memcached",
        "mongodb",
        "redis",
    )
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

        software_version = None
        if module == "cassandra":
            for cluster in scan.get("result", {}).get("data", {}).get("cluster", []):
                if "cassandraVersion" in cluster:
                    software_version = cluster["cassandraVersion"]
        elif module == "elasticsearch" or module == "memcached":
            if "version" in scan.get("result", {}).get("data", {}):
                software_version = scan["result"]["data"]["version"]
            # (potential) TODO: jvm.version, jvm.vm_version, jvm.vm_vendor
        elif module == "mongodb":
            if "version" in scan.get("result", {}).get("data", {}).get("serverInfo"):
                software_version = scan["result"]["data"]["serverInfo"]["version"]
            # (potential) TODO: 'serverInfo.OpenSSLVersion, scan['result']['data']['serverInfo']['openssl']{running,compiled}
            # (potential) TODO: buildEnvironment.cc
        elif module == "redis":
            if "redis_version" in scan.get("result", {}).get("data", {}):
                software_version = scan["result"]["data"]["redis_version"]
            # (potential) TODO: data.gccversion

        if software_version:
            software_ooi = Software(name=module, version=software_version)
        else:
            software_ooi = Software(name=module)
        yield software_ooi
        software_instance_ooi = SoftwareInstance(
            ooi=ip_port_ooi.reference, software=software_ooi.reference
        )
        yield software_instance_ooi

        kat_ooi = KATFindingType(id="KAT-641")
        yield kat_ooi
        yield Finding(
            finding_type=kat_ooi.reference,
            ooi=software_instance_ooi.reference,
            description=f"Database {module.capitalize()} should not be exposed to the internet.",
        )
