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
    network_reference = Network(name="internet").reference

    for event in results:
        # TODO: add event["time"] to results. This is the time the event was first seen. Date of last scan is not
        #  included in the result.
        # TODO: LeakIX want to include a confidence per plugin, since some plugins have more false positives than others
        # TODO: ssh, ssl

        # reset loop
        event_ooi_reference = pk_ooi

        # Autonomous System
        as_ooi = None
        if event["network"]["asn"]:
            as_ooi = handle_autonomous_system(event)
            yield as_ooi

        if event["ip"]:
            for ooi in list(handle_ip(event, network_reference, as_ooi.reference)):
                yield ooi
            # we only need the last ooi's reference
            event_ooi_reference = ooi.reference
            ip_port_ooi_reference = event_ooi_reference
                       
        if event["host"]:
            host_ooi = handle_hostname(event, network_reference)
            yield ooi
            event_ooi_reference = ooi.reference

        software_ooi = None
        for ooi in list(handle_software(event, event_ooi_reference)):
            yield ooi
            if type(ooi) is Software:
                # Leak and CVE Events are bound to the software, not the softwareinstance
                software_ooi = ooi

        # Leak
        yield from handle_leak(event, event_ooi_reference, software_ooi)

        # CVES
        yield from handle_tag(event, software_ooi.reference, ip_port_ooi_reference)


def handle_autonomous_system(event):
    as_number = event["network"]["asn"]
    as_name = event["network"]["organization_name"]
    return AutonomousSystem(number=as_number, name=as_name) if as_name else AutonomousSystem(number=as_number)


def handle_ip(event, network_reference, as_ooi_reference):
    # Store IP
    ip = event["ip"]
    ipvx = ipaddress.ip_address(ip)
    netblock_range = event["network"]["network"].split("/")
    if ipvx.version == 4:
        ip_type = IPAddressV4
        block_type = IPV4NetBlock
    else:
        ip_type = IPAddressV6
        block_type = IPV6NetBlock

    ip_ooi = ip_type(address=ip, network=network_reference)
    yield ip_ooi
    
    if as_ooi and len(netblock_range) == 2:
        yield block_type(
            network=network_reference,
            start_ip=ip_ooi.reference,
            mask=netblock_range[1],
            announced_by=as_ooi_reference,
        )

    # Store port
    ip_port_ooi = IPPort(
        address=ip_ooi.reference,
        protocol=Protocol("tcp" if event["protocol"] != "udp" else "udp"),
        port=int(event["port"]),
        state=PortState("open"),
    )
    yield ip_port_ooi


def handle_hostname(event, network_reference):
    try:
        ipvx = ipaddress.ip_address(event["ip"])
        if ipvx.version == 4:
            return IPAddressV4(address=event["host"], network=network_reference)
        return IPAddressV6(address=event["host"], network=network_reference)
    except ValueError:
        # Not an IPAddress, so a hostname
        return Hostname(name=event["host"], network=network_reference)


def handle_software(event, event_ooi_reference):
    software_args = {}
    software_args["name"] = event.get("service", {}).get("software", {}).get("name")
    software_args["version"] = event.get("service", {}).get("software", {}).get("version")
    software_fingerprint = event.get("service", {}).get("software", {}).get("fingerprint")
    if software_fingerprint:
        software_args["name"] = software_fingerprint

    if software_args["name"]:
        software_ooi = Software(**{k: v for k, v in software_args if v})
        yield software_ooi
        software_instance_ooi = SoftwareInstance(ooi=event_ooi_reference, software=software_ooi.reference)
        yield software_instance_ooi


def handle_leak(event, event_ooi_reference, software_ooi):
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
            kat_info.append(f'Plugin = "{event_source_reference}".')

        if leak_infected:
            kat_info.append("Found evidence of external activity.")
        if leak_ransomnote:
            kat_info.append("Found a ransom note.")
        if leak_stage:
            kat_info.append(f"Stage of the leak is: {leak_stage}.")

        yield Finding(
            finding_type=finding_type.reference,
            ooi=software_ooi.reference if software_ooi or event_source_reference,
            description=", ".join(kat_info),
        )


def handle_tag(event, software_ooi_reference=None, ip_port_ooi_reference=None):
    # Tags (CVE's)
    if isinstance(event.get("tags"), Iterable):
        for tag in event.get("tags", {}):
            if re.match("cve-[0-9]{4}-[0-9]{4,6}", tag):
                ft = CVEFindingType(id=tag)
                cve_ooi = software_ooi_reference if software_ooi_reference else ip_port_ooi_reference
                f = Finding(finding_type=ft.reference, ooi=cve_ooi.reference)
                yield ft
                yield f
