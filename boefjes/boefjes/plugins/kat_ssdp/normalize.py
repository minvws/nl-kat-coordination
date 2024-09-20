import logging
from typing import Iterator, Union

from urllib.parse import urlparse, urlunparse
from ipaddress import ip_address
import json

from octopoes.models import OOI, Reference

from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.network import IPAddressV4, IPAddressV6, Network, IPPort, Protocol
from octopoes.models.ooi.web import WebScheme, Website, IPAddressHTTPURL, HostnameHTTPURL
from octopoes.models.ooi.service import Service, IPService

from boefjes.job_models import NormalizerMeta


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterator[OOI]:
    """parse SSDP output and yield relevant devices, urls and ips."""
    ssdpresponses = json.loads(raw)

    # Relevant network object is received from the normalizer_meta.
    network = Network(name=normalizer_meta.raw_data.boefje_meta.arguments["input"]["network"]["name"])
    yield network
    network_reference = network.reference

    netblock_reference = None
    if "NetBlock" in normalizer_meta.raw_data.boefje_meta.arguments["input"]["object_type"]:
        netblock_reference = Reference.from_str(normalizer_meta.raw_data.boefje_meta.input_ooi)

    logging.info("Parsing SSDP output for %s.", network)
    for response in ssdpresponses:
        # {'location': 'http://192.168.178.1:49000/igddesc.xml',
        # 'server': 'Myaddress UPnP/1.0 AVM FRITZ!Box 7490 113.07.29',
        # 'cache-control': 'max-age=1800',
        # 'ext': '',
        # 'st': 'urn:schemas-upnp-org:service:WANIPv6FirewallControl:1',
        # 'usn': 'uuid:76802409-bccb-40e7-8e6a-3431C48AE71A::urn:schemas-upnp-org:service:WANIPv6FirewallControl:1'}

        url = urlparse(response["location"])

        service = Service(name=url.scheme)
        yield service

        try:
            port = url.port
        except ValueError:
            # urllib might not have given us a port
            port = 443 if url.scheme == "https" else 80

        try:
            # we might get a Hostname instead of an IP due to local MDNS
            ip = ip_address(url.netloc)
        except ValueError:
            ip = False

        if ip:
            # create either an IPV4 or an IPV6 address ooi
            ip = (
                IPAddressV4(network=network_reference, address=ip)
                if host.version == 4
                else IPAddressV6(network=network_reference, address=ip)
            )
            yield ip

            # Create the accompanying port
            ip_port = IPPort(address=ip.reference, protocol=Protocol.TCP, port=port)
            yield ip_port

            # create the service
            ip_service = IPService(ip_port=ip_port.reference, service=service.reference)
            yield ip_service

        else:
            hostname = Hostname(name=url.netloc, network=network_reference)
            yield hostname

        partialpath = urlunparse((url.path, url.fragment, url.query))
        urltype = HostnameHTTPURL
        if ip:
            urltype = IPAddressHTTPURL
            netloc = ip.reference
        else:
            website = Website(hostname=hostname.reference, ip_service=ip_service.reference)
            yield website
            netloc = hostname.reference

        url_ooi = urltype(
            network=network_reference, scheme=WebScheme[url.scheme], port=port, path=partialpath, netloc=netloc
        )
        yield url_ooi

        httpresource = HTTPResource(website=website.reference, web_url=url_ooi.reference)
        yield httpresource

        yield SSDPService(httpresource=httpresource.reference, server=reponse['server'], usn=response['usn'], st=response['st'])
