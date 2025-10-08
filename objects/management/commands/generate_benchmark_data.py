import random
import socket
import struct
from typing import Any

from django.core.management.base import BaseCommand, CommandParser

from objects.models import (
    DNSAAAARecord,
    DNSARecord,
    DNSCAARecord,
    DNSMXRecord,
    DNSNSRecord,
    DNSTXTRecord,
    Hostname,
    IPAddress,
    IPPort,
    Network,
    ScanLevel,
    bulk_insert,
)
from openkat.models import Organization


def generate(
    organization: Organization,
    N: int,
    hostname_scan_level: int,
    ipaddress_scan_level: int,
    port_scan_level: int,
    include_dns_records: bool = False,
) -> tuple[
    list[Hostname],
    list[IPAddress],
    list[IPPort],
    list[DNSARecord],
    list[DNSAAAARecord],
    list[DNSNSRecord],
    list[DNSMXRecord],
    list[DNSTXTRecord],
    list[DNSCAARecord],
    list[ScanLevel],
]:
    network, created = Network.objects.get_or_create(name="internet")
    ips = []
    ips_v6 = []
    ports = []
    hostnames = []
    a_records = []
    aaaa_records = []
    ns_records = []
    mx_records = []
    txt_records = []
    caa_records = []
    scan_levels = []

    for i in range(N):
        # IPv4
        ip = IPAddress(
            network=network,
            address=str(socket.inet_ntoa(struct.pack(">I", random.randint(1, 0xFFFFFFFF)))),  # noqa: S311
        )
        ips.append(ip)

        # IPv6 (every 5th host gets IPv6)
        if include_dns_records and i % 5 == 0:
            ipv6 = IPAddress(network=network, address=f"2001:db8:{i:04x}::{i:04x}")
            ips_v6.append(ipv6)

        # Ports
        http_port = IPPort(address=ip, protocol="TCP", port=80, service="http")
        ports.append(http_port)
        https_port = IPPort(address=ip, protocol="TCP", port=443, service="https")
        ports.append(https_port)

        # Add some varied ports for business rule testing
        if i % 10 == 0:
            ports.append(IPPort(address=ip, protocol="TCP", port=22, service="ssh"))  # Sysadmin port
        if i % 15 == 0:
            ports.append(IPPort(address=ip, protocol="TCP", port=3306, service="mysql"))  # Database port

        # Hostname
        hn = Hostname(network=network, name=f"test_{i}.com")
        hostnames.append(hn)

        # DNS A Record
        a_record = DNSARecord(hostname=hn, ip_address=ip, ttl=300)
        a_records.append(a_record)

        # Additional DNS records (for business rule testing)
        if include_dns_records:
            # AAAA records (IPv6) for every 5th host
            if i % 5 == 0 and ips_v6:
                aaaa_records.append(DNSAAAARecord(hostname=hn, ip_address=ips_v6[-1], ttl=300))

            # NS records for nameservers (every 20th)
            if i % 20 == 0 and i > 0:
                ns_hostname = Hostname(network=network, name=f"ns{i}.test.com")
                hostnames.append(ns_hostname)
                ns_records.append(DNSNSRecord(hostname=hn, name_server=ns_hostname, ttl=300))

            # MX records for mail servers (every 10th)
            if i % 10 == 0 and i > 0:
                mx_hostname = Hostname(network=network, name=f"mail{i}.test.com")
                hostnames.append(mx_hostname)
                mx_records.append(DNSMXRecord(hostname=hn, mail_server=mx_hostname, preference=10, ttl=300))

            # TXT records (every 7th) - some with SPF
            if i % 7 == 0:
                if i % 14 == 0:
                    txt_records.append(DNSTXTRecord(hostname=hn, value="v=spf1 include:_spf.example.com ~all", ttl=300))
                else:
                    txt_records.append(DNSTXTRecord(hostname=hn, value="v=DKIM1; k=rsa; p=...", ttl=300))

            # CAA records (every 25th)
            if i % 25 == 0:
                caa_records.append(DNSCAARecord(hostname=hn, flags=0, tag="issue", value="letsencrypt.org", ttl=300))

        # Scan levels
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

    return (
        hostnames,
        ips + ips_v6,
        ports,
        a_records,
        aaaa_records,
        ns_records,
        mx_records,
        txt_records,
        caa_records,
        scan_levels,
    )


class Command(BaseCommand):
    help = "Load many objects into XTDB"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("-o", dest="organization_code", type=str)
        parser.add_argument("-n", dest="number_of_objects", type=int, default=100_000)
        parser.add_argument("-hs", dest="hostname_scan_level", type=int, default=2)
        parser.add_argument("-is", dest="ipaddress_scan_level", type=int, default=2)
        parser.add_argument("-ps", dest="port_scan_level", type=int, default=2)
        parser.add_argument(
            "--with-dns",
            "-d",
            dest="include_dns",
            action="store_true",
            help="Include additional DNS records for business rule testing",
        )

    def handle(
        self,
        number_of_objects: int,
        hostname_scan_level: int,
        ipaddress_scan_level: int,
        port_scan_level: int,
        organization_code: str,
        include_dns: bool = False,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self.stdout.write(self.style.SUCCESS("Loading benchmark data..."))

        organization = Organization.objects.get(code=organization_code)
        hosts, ips, ports, arecords, aaaa_records, ns_records, mx_records, txt_records, caa_records, levels = generate(
            organization, number_of_objects, hostname_scan_level, ipaddress_scan_level, port_scan_level, include_dns
        )

        self.stdout.write(self.style.SUCCESS("Loading hostnames..."))
        bulk_insert(hosts)

        self.stdout.write(self.style.SUCCESS("Loading ipaddresses..."))
        bulk_insert(ips)

        self.stdout.write(self.style.SUCCESS("Loading ipports..."))
        bulk_insert(ports)

        self.stdout.write(self.style.SUCCESS("Loading DNSArecords..."))
        bulk_insert(arecords)

        if include_dns:
            if aaaa_records:
                self.stdout.write(self.style.SUCCESS("Loading DNSAAAArecords..."))
                bulk_insert(aaaa_records)
            if ns_records:
                self.stdout.write(self.style.SUCCESS("Loading DNSNSrecords..."))
                bulk_insert(ns_records)
            if mx_records:
                self.stdout.write(self.style.SUCCESS("Loading DNSMXrecords..."))
                bulk_insert(mx_records)
            if txt_records:
                self.stdout.write(self.style.SUCCESS("Loading DNSTXTrecords..."))
                bulk_insert(txt_records)
            if caa_records:
                self.stdout.write(self.style.SUCCESS("Loading DNSCAArecords..."))
                bulk_insert(caa_records)

        self.stdout.write(self.style.SUCCESS("Loading scan levels..."))
        bulk_insert(levels)
