import ipaddress
import json
import re
from collections.abc import Iterable
from typing import Iterator, Union

from octopoes.models import OOI, Reference
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.findings import KATFindingType, Finding, CVEFindingType
from octopoes.models.ooi.network import (
    IPPort,
    Protocol,
    PortState,
    IPAddressV4,
    IPAddressV6,
    AutonomousSystem,
    Network,
    IPV4NetBlock,
    IPV6NetBlock,
)
from octopoes.models.ooi.software import Software, SoftwareInstance

from job import NormalizerMeta


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterator[OOI]:
    results = json.loads(raw)

    boefje_meta = normalizer_meta.boefje_meta
    pk_ooi = Reference.from_str(boefje_meta.input_ooi)
    network = Network(name="internet").reference

    for event in results:
        # Future TODO: add event["time"] to results. This is the time the event was first seen. Date of last scan is not included in the result.
        # Future TODO: LeakIX want to include a confidence per plugin, since some plugins have more false positives than others
        # Potential TODO: ssh, ssl

        # Get general information
        ip = event["ip"]
        port_nr = event["port"]
        protocol = event["protocol"]
        if protocol != "udp":
            protocol = "tcp"
        event_ooi = pk_ooi

        # Autonomous System
        as_number = event["network"]["asn"]
        as_name = event["network"]["organization_name"]
        if as_number:
            if as_name:
                as_ooi = AutonomousSystem(number=as_number, name=as_name)
            else:
                as_ooi = AutonomousSystem(number=as_number)
            yield as_ooi

        if ip:
            # Store IP
            ipvx = ipaddress.ip_address(ip)
            netblock_range = event["network"]["network"].split("/")
            if ipvx.version == 4:
                ip_ooi = IPAddressV4(address=ip, network=network)
                if as_number and len(netblock_range) == 2:
                    yield IPV4NetBlock(
                        network=network,
                        start_ip=ip_ooi,
                        mask=netblock_range[1],
                        announced_by=as_ooi.reference,
                    )
            else:
                ip_ooi = IPAddressV6(address=ip, network=network)
                if as_number and len(netblock_range) == 2:
                    yield IPV6NetBlock(
                        network=network,
                        start_ip=ip_ooi,
                        mask=netblock_range[1],
                        announced_by=as_ooi.reference,
                    )
            yield ip_ooi
            event_ooi = ip_ooi.reference

            # Store port
            ip_port_ooi = IPPort(
                address=ip_ooi.reference,
                protocol=Protocol(protocol),
                port=int(port_nr),
                state=PortState("open"),
            )
            yield ip_port_ooi
            event_ooi = ip_port_ooi.reference

        hostname = event["host"]
        if hostname:
            try:
                ipvx = ipaddress.ip_address(ip)
                if ipvx.version == 4:
                    ip_ooi = IPAddressV4(address=hostname, network=network)
                else:
                    ip_ooi = IPAddressV6(address=hostname, network=network)
                yield ip_ooi
                event_ooi = ip_ooi.reference

            except ValueError:
                # Not an IPAddress, so a hostname
                hostname_ooi = Hostname(name=hostname, network=network)
                yield hostname_ooi
                event_ooi = hostname_ooi.reference

        # Service
        software_ooi = None
        software_name = event.get("service", {}).get("software", {}).get("name")
        software_version = event.get("service", {}).get("software", {}).get("version")
        software_fingerprint = (
            event.get("service", {}).get("software", {}).get("fingerprint")
        )
        if software_name:
            if software_version:
                software_ooi = Software(name=software_name, version=software_version)
            else:
                software_ooi = Software(name=software_name)
        elif software_fingerprint:
            software_ooi = Software(name=software_fingerprint)
        if software_ooi:
            yield software_ooi
            software_instance_ooi = SoftwareInstance(
                ooi=event_ooi, software=software_ooi.reference
            )
            yield software_instance_ooi
            event_ooi = software_instance_ooi.reference
        # Potential TODO: add vendor

        # Leak
        leak_severity = event.get("leak", {}).get("severity")
        event_source = event.get("event_source")
        leak_stage = event.get("leak", {}).get("dataset", {}).get("stage")
        if leak_severity or leak_stage:
            #  Got the differen severities from: https://pkg.go.dev/github.com/LeakIX/l9format#pkg-constants
            leak_infected = event.get("leak", {}).get("dataset", {}).get("infected")
            leak_ransomnote = (
                event.get("leak", {}).get("dataset", {}).get("ransom_notes")
            )
            if leak_severity == "critical" or leak_infected or leak_ransomnote:
                kat_number = "KAT-645"
            elif leak_severity == "high":
                kat_number = "KAT-646"
            elif leak_severity == "medium":
                kat_number = "KAT-647"
            elif leak_severity == "low":
                kat_number = "KAT-648"
            elif leak_severity == "info":
                kat_number = "KAT-649"
            elif leak_stage == "open":
                # no severity given, default = low
                kat_number = "KAT-648"
            elif leak_stage == "explore":
                # no severity given, default = high
                kat_number = "KAT-646"
            elif leak_stage == "exfiltrate":
                # no severity given, default = critical
                kat_number = "KAT-645"
            else:
                # new stage or severity, default to low
                kat_number = "KAT-648"

            kat_ooi = KATFindingType(id=kat_number)
            kat_info = []
            if software_ooi:
                kat_info.append(f'Software = "{software_ooi.name}".')
            else:
                kat_info.append(f'Plugin = "{event_source}"')
            if leak_infected:
                kat_info.append(f"Found evidence of external activity.")
            if leak_ransomnote:
                kat_info.append(f"Found a ransom note.")

            if leak_stage:
                kat_info.append(f"Stage of the leak is {leak_stage}.")

            kat_description = " ".join(kat_info)
            yield kat_ooi
            yield Finding(
                finding_type=kat_ooi.reference,
                ooi=event_ooi,
                description=kat_description,
            )

        # Tags (CVE's)
        if isinstance(event.get("tags"), Iterable):
            for tag in event.get("tags", {}):
                if re.match("cve-[0-9]{4}-[0-9]{4,6}", tag):
                    ft = CVEFindingType(id=tag)
                    if software_ooi:
                        cve_ooi = software_ooi
                    else:
                        cve_ooi = ip_port_ooi
                    f = Finding(finding_type=ft.reference, ooi=cve_ooi.reference)
                    yield ft
                    yield f
