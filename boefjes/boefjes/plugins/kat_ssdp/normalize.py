import json
import logging
from collections.abc import Iterator
from ipaddress import ip_address
from typing import Literal
from urllib.parse import urlparse

from octopoes.models import OOI, Reference
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.network import IPAddressV4, IPAddressV6, IPPort, Network, Protocol
from octopoes.models.ooi.service import IPService, Service
from octopoes.models.ooi.web import HostnameHTTPURL, HTTPResource, IPAddressHTTPURL, WebScheme, Website, WebURL
from octopoes.models.persistence import ReferenceField


def run(input_ooi: dict, raw: bytes | str) -> Iterator[OOI]:
    """parse SSDP output and yield relevant devices, urls and ips."""

    ssdp_responses: list[dict[str, str]] = json.loads(raw)

    network = Network(name=input_ooi["name"])
    yield network
    network_reference = network.reference

    logging.info("Parsing SSDP output for %s.", network)
    for response in ssdp_responses:
        url = None
        try:
            url = urlparse(response["location"])
            logging.info(url)
        except KeyError as e:
            logging.info("Probably found a response without location. Missing key: %s", e)

            yield SSDPResponse(
                network=network.reference,
                nt=response["nt"],
                nts=response["nts"],
                server=response["host"],
                usn=response["usn"],
            )

            continue

        ip = None
        hostname = None

        try:
            service = Service(name=url.scheme)
            yield service

            ip = ip_address(url.netloc.split(":")[0])

            ip_ooi = (
                IPAddressV4(network=network_reference, address=ip)
                if ip.version == 4
                else IPAddressV6(network=network_reference, address=ip)
            )
            yield ip_ooi

            if url.port:
                port = url.port
            else:
                port = 443 if url.scheme == "https" else 80

            # Create the accompanying port
            ip_port = IPPort(address=ip_ooi.reference, protocol=Protocol.TCP, port=port)
            yield ip_port

            # create the service
            ip_service = IPService(ip_port=ip_port.reference, service=service.reference)
            yield ip_service

        except ValueError:
            logging.info("Response probably contains a hostname instead of an ip")

            hostname = Hostname(name=url.netloc, network=network_reference)
            yield hostname

        if ip and ip_ooi:  # These should always be both assigned or neither should be assigned
            url_ooi = IPAddressHTTPURL(
                network=network_reference,
                scheme=WebScheme(url.scheme),
                port=port,
                path=url.path,
                netloc=ip_ooi.reference,
            )
        else:
            if not hostname:
                logging.error(
                    "Hostname didn't exist while ip also did not exist. This should not be possible. "
                    "With the location: %s",
                    response["location"],
                )
                continue

            url_ooi = HostnameHTTPURL(
                network=network_reference,
                scheme=WebScheme(url.scheme),
                port=port,
                path=url.path,
                netloc=hostname.reference,
            )

            website = Website(hostname=hostname.reference, ip_service=ip_service.reference)
            yield website

            httpresource = HTTPResource(website=website.reference, web_url=url_ooi.reference)
            yield httpresource

        yield url_ooi

        yield SSDPResponse(
            web_url=url_ooi.reference,
            network=network.reference,
            nt=response["nt"],
            nts=response["nts"],
            server=response["host"],
            usn=response["usn"],
        )


class SSDPResponse(OOI):
    """OOI holding information about a found response from SSDP. Example response https://wiki.wireshark.org/SSDP"""

    object_type: Literal["SSDPService"] = "SSDPService"

    web_url: Reference | None = ReferenceField(WebURL, default=None)
    network: Reference = ReferenceField(Network)

    nt: str
    nts: str
    server: str
    usn: str


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="[%(filename)s:%(lineno)s - %(funcName)20s() ] %(message)s",
    )

    for x in run({"name": "aa"}, "{}"):
        logging.info("Yielded: %s", x)
