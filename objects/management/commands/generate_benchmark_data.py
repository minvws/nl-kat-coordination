import random
import socket
import struct
from typing import Any

from django.core.management.base import BaseCommand, CommandParser

from objects.models import DNSARecord, Hostname, IPAddress, IPPort, Network, ScanLevel, bulk_insert
from openkat.models import Organization


def generate(
    organization: Organization, N: int, hostname_scan_level: int, ipaddress_scan_level: int, port_scan_level: int
) -> tuple[list[Hostname], list[IPAddress], list[IPPort], list[DNSARecord], list[ScanLevel]]:
    network, created = Network.objects.get_or_create(name="internet")
    ips = []
    ports = []
    hostnames = []
    a_records = []
    scan_levels = []

    for i in range(N):
        ip = IPAddress(
            network=network,
            address=str(socket.inet_ntoa(struct.pack(">I", random.randint(1, 0xFFFFFFFF)))),  # noqa: S311
        )
        ips.append(ip)

        http_port = IPPort(address=ip, protocol="TCP", port=80, service="http")
        ports.append(http_port)
        https_port = IPPort(address=ip, protocol="TCP", port=443, service="https")
        ports.append(https_port)

        hn = Hostname(network=network, name=f"test_{i}.com")
        hostnames.append(hn)
        a_record = DNSARecord(hostname=hn, ip_address=ip)
        a_records.append(a_record)

        scan_levels.extend(
            [
                ScanLevel(
                    organization=organization, object_type="ipaddress", object_id=ip.id, scan_level=ipaddress_scan_level
                ),
                ScanLevel(
                    organization=organization, object_type="hostname", object_id=hn.id, scan_level=hostname_scan_level
                ),
                ScanLevel(
                    organization=organization, object_type="ipport", object_id=http_port.id, scan_level=port_scan_level
                ),
                ScanLevel(
                    organization=organization, object_type="ipport", object_id=https_port.id, scan_level=port_scan_level
                ),
            ]
        )

    return hostnames, ips, ports, a_records, scan_levels


class Command(BaseCommand):
    help = "Load many objects into XTDB"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("-o", dest="organization_code", type=str)
        parser.add_argument("-n", dest="number_of_objects", type=int, default=100_000)
        parser.add_argument("-hs", dest="hostname_scan_level", type=int, default=2)
        parser.add_argument("-is", dest="ipaddress_scan_level", type=int, default=2)
        parser.add_argument("-ps", dest="port_scan_level", type=int, default=2)

    def handle(
        self,
        number_of_objects: int,
        hostname_scan_level: int,
        ipaddress_scan_level: int,
        port_scan_level: int,
        organization_code: str,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self.stdout.write(self.style.SUCCESS("Loading benchmark data..."))

        organization = Organization.objects.get(code=organization_code)
        hostnames, ips, ports, arecords, scan_levels = generate(
            organization, number_of_objects, hostname_scan_level, ipaddress_scan_level, port_scan_level
        )

        self.stdout.write(self.style.SUCCESS("Loading hostnames..."))
        bulk_insert(hostnames)

        self.stdout.write(self.style.SUCCESS("Loading ipaddresses..."))
        bulk_insert(ips)

        self.stdout.write(self.style.SUCCESS("Loading ipports..."))
        bulk_insert(ports)

        self.stdout.write(self.style.SUCCESS("Loading DNSArecords..."))
        bulk_insert(arecords)

        self.stdout.write(self.style.SUCCESS("Loading scan levels..."))
        bulk_insert(scan_levels)
