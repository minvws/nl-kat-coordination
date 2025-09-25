import random
import socket
import struct
from typing import Any

from django.core.management.base import BaseCommand, CommandParser

from objects.models import Hostname, IPAddress, IPPort, Network, bulk_insert


class Command(BaseCommand):
    help = "Load many objects into XTDB"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("-n", dest="number_of_objects", type=int, default=100_000)

    def handle(self, number_of_objects: int, *args: Any, **kwargs: Any) -> None:
        """Create demo data for the OOI application."""
        self.stdout.write(self.style.SUCCESS("Loading benchmark data..."))

        # Create network
        network, created = Network.objects.get_or_create(name="internet")

        # Create IP addresses
        N = number_of_objects
        ips = []
        ports = []
        hostnames = []
        for i in range(N):
            ip = IPAddress(
                network=network,
                address=str(socket.inet_ntoa(struct.pack(">I", random.randint(1, 0xFFFFFFFF)))),  # noqa: S311
            )
            ips.append(ip)

            ports.append(IPPort(address=ip, protocol="TCP", port=80, service="http"))
            ports.append(IPPort(address=ip, protocol="TCP", port=443, service="https"))
            hostnames.append(Hostname(network=network, name=f"test_{i}.com"))

        self.stdout.write(self.style.SUCCESS("Loading hostnames..."))
        bulk_insert(hostnames)

        self.stdout.write(self.style.SUCCESS("Loading ipaddresses..."))
        bulk_insert(ips)

        self.stdout.write(self.style.SUCCESS("Loading ipports..."))
        bulk_insert(ports)
