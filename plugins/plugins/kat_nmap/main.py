import ipaddress
import json
import logging
import os
import sys
from ipaddress import AddressValueError

import httpx
from libnmap.objects import NmapHost, NmapService
from libnmap.parser import NmapParser


def get_ip_ports_and_service(host: NmapHost):
    """Yields IPs, open ports and services if any ports are open on this host."""
    open_ports = host.get_open_ports()
    ip = f"IPAddressV4|internet|{host.address}" if host.ipv4 else f"IPAddressV6|internet|{host.address}"
    ip_obj = (
        dict(object_type="IPAddressV4", network="Network|internet", address=host.address)
        if host.ipv4
        else dict(object_type="IPAddressV6", network="Network|internet", address=host.address)
    )

    results = [ip_obj]
    if open_ports:
        for port, protocol in open_ports:
            service: NmapService = host.get_service(port, protocol)

            # If service is tcpwrapped we should consider the port closed
            if service.service == "tcpwrapped":
                continue

            ip_port = dict(object_type="IPPort", address=ip, protocol=protocol, port=port, state=service.state)
            results.append(ip_port)

            service_name = service.service
            if service_name == "http" and service.tunnel == "ssl":
                service_name = "https"

            port_service = dict(object_type="Service", name=service_name)
            results.append(port_service)

            ip_service = dict(
                object_type="IPService",
                ip_port=f"IPPort|internet|{host.address}|{protocol}|{ip_port['port']}",
                service=f"Service|{service_name}",
            )  # TODO
            results.append(ip_service)

    return results


def run(file_id: str):
    headers = {"Authorization": "Token " + os.getenv("OPENKAT_TOKEN")}
    client = httpx.Client(base_url=os.getenv("OPENKAT_API"), headers=headers)

    dig_file = client.get(f"/file/{file_id}/").json()
    file = client.get(dig_file["file"])

    """Decouple and parse Nmap XMLs and yield relevant network."""
    # Multiple XMLs are concatenated through "\n\n". XMLs end with "\n"; we split on "\n\n\n".
    raw_splitted = file.content.decode().split("\n\n\n")

    # Relevant network object is received from the normalizer_meta.
    results = []
    logging.info("Parsing %d Nmap-xml(s).", len(raw_splitted))

    for nmap_output in raw_splitted:
        results.extend(handle_nmap_result(nmap_output, client))

    return results


def handle_nmap_result(nmap_output: str, client: httpx.Client):
    results = []
    parsed = NmapParser.parse_fromstring(nmap_output)

    try:
        *args, target = parsed.commandline.split(" ")
    except KeyError:
        args = []

    top_ports = None

    if "--top-ports" in args:
        top_ports = int(args[args.index("--top-ports") + 1])

    for host in parsed.hosts:
        # TODO: handle this in the API
        client.delete(f"/objects/ip-ports/?address={host.address}&top_ports={top_ports}")

        results.extend(get_ip_ports_and_service(host=host))

    return results


if __name__ == "__main__":
    oois = run(sys.argv[1])
    headers = {"Authorization": "Token " + os.getenv("OPENKAT_TOKEN")}
    httpx.post(f'{os.getenv("OPENKAT_API")}/objects/', headers=headers, json=oois)

    print(json.dumps(oois))
