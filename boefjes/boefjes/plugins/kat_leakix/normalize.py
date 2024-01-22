import ipaddress
import json
import re
from collections.abc import Iterable
from typing import Iterable as Iterable_
from typing import Union

from boefjes.job_models import NormalizerMeta
from octopoes.models import OOI, Reference
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.findings import CVEFindingType, Finding, KATFindingType
from octopoes.models.ooi.network import (
    AutonomousSystem,
    IPAddressV4,
    IPAddressV6,
    IPPort,
    IPV4NetBlock,
    IPV6NetBlock,
    Network,
    PortState,
    Protocol,
)
from octopoes.models.ooi.software import Software, SoftwareInstance

SEVERITY_FINDING_MAPPING = {
    "high": "KAT-LEAKIX-HIGH",
    "medium": "KAT-LEAKIX-MEDIUM",
    "low": "KAT-LEAKIX-LOW",
    "info": "KAT-LEAKIX-RECOMMENDATION",
}


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterable_[OOI]:
    results = json.loads(raw)

    boefje_meta = normalizer_meta.raw_data.boefje_meta
    pk_ooi = Reference.from_str(boefje_meta.input_ooi)
    network = Network(name="internet").reference

    for event in results:
        # TODO: add event["time"] to results. This is the time the event was first seen. Date of last scan is not
        #  included in the result.
        # TODO: LeakIX want to include a confidence per plugin, since some plugins have more false positives than others
        # TODO: ssh, ssl

        # reset loop
        event_ooi = pk_ooi

        # Autonomous System
        as_ooi = None
        if event["network"]["asn"]:
            as_ooi = handle_autonomous_system(event)

        if event["ip"]:
            event_ooi, ip_port_ooi = handle_ip(event, network, as_ooi)

        if event["host"]:
            event_ooi = handle_hostname(event, network)

        event_ooi, software_ooi = handle_software(event, event_ooi)
        # Potential TODO: add vendor

        # Leak
        handle_leak(event, event_ooi, software_ooi)

        # CVES
        handle_tag(event, software_ooi, ip_port_ooi)


def handle_autonomous_system(event):
    as_number = event["network"]["asn"]
    as_name = event["network"]["organization_name"]
    as_ooi = AutonomousSystem(number=as_number, name=as_name) if as_name else AutonomousSystem(number=as_number)
    yield as_ooi
    return as_ooi


def handle_ip(event, network, as_ooi):
    # Store IP
    ip = event["ip"]
    ipvx = ipaddress.ip_address(ip)
    netblock_range = event["network"]["network"].split("/")
    if ipvx.version == 4:
        iptype = IPAddressV4
        blocktype = IPV4NetBlock
    else:
        iptype = IPAddressV6
        blocktype = IPV6NetBlock

    ip_ooi = iptype(address=ip, network=network)
    yield ip_ooi
    event_ooi = ip_ooi.reference
    if as_ooi and len(netblock_range) == 2:
        yield blocktype(
            network=network,
            start_ip=ip_ooi,
            mask=netblock_range[1],
            announced_by=as_ooi.reference,
        )

    # Store port
    protocol = event["protocol"]
    if protocol != "udp":
        protocol = "tcp"

    ip_port_ooi = IPPort(
        address=ip_ooi.reference,
        protocol=Protocol(protocol),
        port=int(event["port"]),
        state=PortState("open"),
    )
    yield ip_port_ooi
    event_ooi = ip_port_ooi.reference
    return event_ooi, ip_port_ooi


def handle_hostname(event, network):
    try:
        ipvx = ipaddress.ip_address(event["ip"])
        if ipvx.version == 4:
            ip_ooi = IPAddressV4(address=event["host"], network=network)
        else:
            ip_ooi = IPAddressV6(address=event["host"], network=network)
        yield ip_ooi
        return ip_ooi.reference
    except ValueError:
        # Not an IPAddress, so a hostname
        hostname_ooi = Hostname(name=event["host"], network=network)
        yield hostname_ooi
        return hostname_ooi.reference


def handle_software(event, event_ooi):
    software_args = {}
    software_args["name"] = event.get("service", {}).get("software", {}).get("name")
    software_args["version"] = event.get("service", {}).get("software", {}).get("version")
    software_fingerprint = event.get("service", {}).get("software", {}).get("fingerprint")
    if software_fingerprint:
        software_args["name"] = software_fingerprint

    if software_args["name"]:
        software_ooi = Software(**{k: v for k, v in software_args if v})
        yield software_ooi
        software_instance_ooi = SoftwareInstance(ooi=event_ooi, software=software_ooi.reference)
        yield software_instance_ooi
        event_ooi = software_instance_ooi.reference
        return event_ooi, software_ooi
    return event_ooi, None


def handle_leak(event, event_ooi, software_ooi):
    leak_severity = event.get("leak", {}).get("severity")
    event_source = event.get("event_source")
    leak_stage = event.get("leak", {}).get("dataset", {}).get("stage")
    if leak_severity or leak_stage:
        #  Got the different severities from: https://pkg.go.dev/github.com/LeakIX/l9format#pkg-constants
        leak_infected = event.get("leak", {}).get("dataset", {}).get("infected")
        leak_ransomnote = event.get("leak", {}).get("dataset", {}).get("ransom_notes")

        # new stage or severity, default to low
        kat_finding = "KAT-LEAKIX-LOW"
        if leak_severity == "critical" or leak_infected or leak_ransomnote:
            kat_finding = "KAT-LEAKIX-CRITICAL"
        elif leak_severity in SEVERITY_FINDING_MAPPING:
            kat_finding = SEVERITY_FINDING_MAPPING[leak_severity]
        elif leak_stage == "open":
            # no severity given, default = low
            kat_finding = "KAT-LEAKIX-LOW"
        elif leak_stage == "explore":
            # no severity given, default = high
            kat_finding = "KAT-LEAKIX-HIGH"
        elif leak_stage == "exfiltrate":
            # no severity given, default = critical
            kat_finding = "KAT-LEAKIX-CRITICAL"

        finding_type = KATFindingType(id=kat_finding)
        yield finding_type

        kat_info = []
        if software_ooi:
            kat_info.append(f'Software = "{software_ooi.name}".')
        else:
            kat_info.append(f'Plugin = "{event_source}"')

        if leak_infected:
            kat_info.append("Found evidence of external activity.")
        if leak_ransomnote:
            kat_info.append("Found a ransom note.")
        if leak_stage:
            kat_info.append(f"Stage of the leak is {leak_stage}.")

        yield Finding(
            finding_type=finding_type.reference,
            ooi=event_ooi,
            description=" ".join(kat_info),
        )


def handle_tag(event, software_ooi=None, ip_port_ooi=None):
    # Tags (CVE's)
    if isinstance(event.get("tags"), Iterable):
        for tag in event.get("tags", {}):
            if re.match("cve-[0-9]{4}-[0-9]{4,6}", tag):
                ft = CVEFindingType(id=tag)
                cve_ooi = software_ooi if software_ooi else ip_port_ooi
                f = Finding(finding_type=ft.reference, ooi=cve_ooi.reference)
                yield ft
                yield f
