import json
import logging
import os
import sys
from collections import defaultdict

import httpx
from httpx import HTTPError
from libnmap.objects import NmapHost, NmapReport, NmapService
from libnmap.parser import NmapParser


def get_ip_ports_and_service(host: NmapHost, internet_id: int):
    """Yields IPs, open ports and services if any ports are open on this host."""
    open_ports = host.get_open_ports()
    ip_obj = {"object_type": "IPAddress", "network": internet_id, "address": host.address}

    results = [ip_obj]
    if open_ports:
        for port, protocol in open_ports:
            service: NmapService = host.get_service(port, protocol)

            # If service is tcpwrapped we should consider the port closed
            if service.service == "tcpwrapped":
                continue
            service_name = service.service
            if service_name == "http" and service.tunnel == "ssl":
                service_name = "https"

            ip_port = {
                "object_type": "IPPort",
                "address": ip_obj["address"],
                "protocol": protocol,
                "port": port,
                "state": service.state,
                "service": service_name,
            }
            results.append(ip_port)

    return results


def run(file_id: str):
    token = os.getenv("OPENKAT_TOKEN")
    if not token:
        raise Exception("No OPENKAT_TOKEN env variable")

    base_url = os.getenv("OPENKAT_API")
    if not base_url:
        raise Exception("No OPENKAT_API env variable")

    headers = {"Authorization": "Token " + token}
    client = httpx.Client(base_url=base_url, headers=headers)

    nmap_file = client.get(f"/file/{file_id}/").json()
    file = client.get(nmap_file["file"])

    # Multiple XMLs are concatenated through "\n\n". XMLs end with "\n"; we split on "\n\n\n".
    raw_splitted = file.content.decode().split("\n\n\n")

    # Relevant network object is received from the normalizer_meta.
    results = []
    logging.info("Parsing %d Nmap-xml(s).", len(raw_splitted))

    response = client.get("/objects/network/", params={"name": "internet", "limit": 1}).json()

    if not response["results"]:
        internet = client.post("/objects/network/", json={"name": "internet"}).json()
    else:
        internet = response["results"][0]

    for nmap_output in raw_splitted:
        parsed = NmapParser.parse_fromstring(nmap_output)
        ports_scanned = get_ports_scanned(parsed)

        for host in parsed.hosts:
            result = get_ip_ports_and_service(host, internet["id"])

            response = client.get("/objects/ipaddress/", params={"address": str(host.address), "limit": 1}).json()

            if not response["results"]:
                address = client.post(
                    "/objects/ipaddress/", json={"address": str(host.address), "network": internet["id"]}
                ).json()
            else:
                address = response["results"][0]

            open_ports = [ooi["port"] for ooi in result if ooi["object_type"] == "IPPort" and ooi["state"] == "open"]
            params = {"port": ports_scanned, "address": address["id"]}
            ports = [x["id"] for x in client.get("/objects/ipport/", params=params).json()["results"]]

            try:
                client.delete("/objects/ipport/", params={"pk": list(set(ports) - set(open_ports))})
            except HTTPError:
                print(f"Failed to delete ports for {host}, continuing")  # noqa: T201
                continue

            results.extend(result)

    results_grouped = defaultdict(list)
    for result in results:
        results_grouped[result.pop("object_type").lower()].append(result)

    ips = client.post("/objects/ipaddress/", headers=headers, json=results_grouped.pop("ipaddress")).json()
    by_address = {ip["address"]: ip["id"] for ip in ips}

    for object_path, objects in results_grouped.items():
        for obj in objects:
            if "address" in obj:
                obj["address"] = by_address[obj["address"]]

        client.post(f"/objects/{object_path.lower()}/", json=results)

    return results


def get_ports_scanned(parsed: NmapReport):
    """Given an NmapReport, get the list of ports that were actually scanned"""

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
    results = run(sys.argv[1])

    print(json.dumps(results))  # noqa: T201
