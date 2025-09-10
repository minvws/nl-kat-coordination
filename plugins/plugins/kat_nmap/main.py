import json
import logging
import os
import sys

import httpx
from httpx import HTTPError
from libnmap.objects import NmapHost, NmapReport, NmapService
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
                ip_port=f"IPPort|internet|{host.address}|{ip_port['protocol']}|{ip_port['port']}",
                service=f"Service|{service_name}",
            )  # TODO
            results.append(ip_service)

    return results


def run(file_id: str):
    headers = {"Authorization": "Token " + os.getenv("OPENKAT_TOKEN")}
    client = httpx.Client(base_url=os.getenv("OPENKAT_API"), headers=headers)

    nmap_file = client.get(f"/file/{file_id}/").json()
    file = client.get(nmap_file["file"])

    # Multiple XMLs are concatenated through "\n\n". XMLs end with "\n"; we split on "\n\n\n".
    raw_splitted = file.content.decode().split("\n\n\n")

    # Relevant network object is received from the normalizer_meta.
    results = []
    logging.info("Parsing %d Nmap-xml(s).", len(raw_splitted))

    for nmap_output in raw_splitted:
        parsed = NmapParser.parse_fromstring(nmap_output)
        ports_scanned = get_ports_scanned(parsed)

        for host in parsed.hosts:
            result = get_ip_ports_and_service(host=host)

            open_ports = [f"IPPort|internet|{host.address}|{ooi['protocol']}|{ooi['port']}"
                          for ooi in result if ooi["object_type"] == "IPPort" and ooi["state"] == "open"]

            # TODO: use address as filter if it's not in the pk anymore.
            params = {"object_type": "IPPort", "port": ports_scanned}
            ports = [x["primary_key"] for x in client.get("/objects/", params=params).json()["results"]]

            try:
                client.delete("/objects/", params={"pk": list(set(ports) - set(open_ports))})
            except HTTPError:
                print(f"Failed to delete ports for {host}, continuing")
                continue

            results.extend(result)

    client.post(f'{os.getenv("OPENKAT_API")}/objects/', json=results)

    return results


def get_ports_scanned(parsed: NmapReport):
    """ Given an NmapReport, get the list of ports that were actually scanned """

    ports_scanned = []

    for port_range in parsed.get_raw_data().get("_scaninfo", {}).get("services", "").split(","):
        if port_range == "":
            continue

        if "-" in port_range:
            begin, end = port_range.split("-", 1)
            ports_scanned.extend(list(range(int(begin), int(end))))
            continue

        ports_scanned.append(int(port_range))

    return ports_scanned


if __name__ == "__main__":
    oois = run(sys.argv[1])

    print(json.dumps(oois))
