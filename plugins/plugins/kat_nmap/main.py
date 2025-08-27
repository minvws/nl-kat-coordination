import ipaddress
import json
import logging
import os
import sys
from ipaddress import AddressValueError

import httpx
from libnmap.objects import NmapHost, NmapService
from libnmap.parser import NmapParser


def get_ip_ports_and_service(host: NmapHost, network: str, prefixlen: str | None):
    """Yields IPs, open ports and services if any ports are open on this host."""
    open_ports = host.get_open_ports()

    results = []
    if open_ports:
        ip = (
            dict(object_type="IPAddressV4", network=network, address=host.address, netblock=prefixlen)
            if host.ipv4
            else dict(object_type="IPAddressV6", network=network, address=host.address, netblock=prefixlen)
        )

        for port, protocol in open_ports:
            service: NmapService = host.get_service(port, protocol)

            # If service is tcpwrapped we should consider the port closed
            if service.service == "tcpwrapped":
                continue

            ip_port = dict(
                object_type="IPPort", address=ip["address"], protocol=protocol, port=port, state=service.state
            )
            results.append(ip_port)

            service_name = service.service
            if service_name == "http" and service.tunnel == "ssl":
                service_name = "https"

            port_service = dict(object_type="Service", name=service_name)
            results.append(port_service)

            ip_service = dict(object_type="IPService", ip_port=ip_port["port"], service=port_service["name"])  # TODO
            results.append(ip_service)

    return results


def run(file_id: str):
    headers = {"Authorization": "Token " + os.getenv("OPENKAT_TOKEN")}
    dig_file = httpx.get(f'{os.getenv("OPENKAT_API")}/file/{file_id}/', headers=headers).json()
    file = httpx.get(dig_file["file"], headers=headers)

    """Decouple and parse Nmap XMLs and yield relevant network."""
    # Multiple XMLs are concatenated through "\n\n". XMLs end with "\n"; we split on "\n\n\n".
    raw_splitted = file.content.decode().split("\n\n\n")

    # Relevant network object is received from the normalizer_meta.
    results = []
    logging.info("Parsing %d Nmap-xml(s).", len(raw_splitted))
    for r in raw_splitted:
        parsed = NmapParser.parse_fromstring(r)
        *args, target = parsed.commandline.split(" ")

        if "/" in target:
            try:
                network = ipaddress.IPv4Network(target)
                prefixlen = network.prefixlen
            except (AddressValueError, ValueError):
                try:
                    network = ipaddress.IPv6Network(target)
                    prefixlen = network.prefixlen
                except (AddressValueError, ValueError):
                    prefixlen = None
        else:
            prefixlen = None

        for host in parsed.hosts:
            results.extend(get_ip_ports_and_service(host=host, network="internet", prefixlen=str(prefixlen)))

    return results


if __name__ == "__main__":
    oois = run(sys.argv[1])
    print(json.dumps(oois))
