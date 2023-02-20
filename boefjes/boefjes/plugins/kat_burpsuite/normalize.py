from xml.dom import minidom
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from ipaddress import ip_address, IPv4Address, IPv6Address
import base64

from typing import Iterator, Union

from octopoes.models import OOI, Reference
from octopoes.models.ooi.findings import Finding, CWEFindingType, CAPECFindingType, CVEFindingType
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.network import IPAddressV4, IPAddressV6, Network, IPPort, Protocol
from octopoes.models.ooi.web import WebScheme, Website, IPAddressHTTPURL, HostnameHTTPURL, URL, HTTPResource, HTTPHeader
from octopoes.models.ooi.service import Service, IPService

from boefjes.job_models import NormalizerMeta


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterator[OOI]:
    parser = minidom.parse(raw)

    # assume that input ooi is none or a HostnameHTTPURL
    if normalizer_meta.raw_data.boefje_meta and normalizer_meta.raw_data.boefje_meta.input_ooi and False:
        ooi = Reference.from_str(normalizer_meta.raw_data.boefje_meta.input_ooi)
        network = Network(name=ooi.tokenized.netloc.network.name)
    else:
        network = Network(name="internet")
        yield network

    tcp_protocol = Protocol.TCP

    # TODO use timestamp for sample to setup new OOI's
    #  with parser.getElementsByTagName('issues').attributes['exportTime'].value

    for issue in parser.getElementsByTagName("issue"):

        host_element = issue.getElementsByTagName("host")[0]
        host = host_element.firstChild.nodeValue

        ip = ip_address(host_element.attributes["ip"].value)
        path = issue.getElementsByTagName("path")[0].firstChild.nodeValue

        yield URL(network=network.reference, raw=f"{host}{path}")

        url = urlparse(f"{host}{path}")

        hostname = None
        # we might be dealing with a request to an IP-address
        if url.netloc != ip:
            hostname = Hostname(name=url.netloc, network=network.reference)
            yield hostname

        port = 443 if url.scheme == "https" else 80

        address = ip_address(ip)
        if isinstance(address, IPv4Address):
            ip = IPAddressV4(address=address, network=network.reference)
        elif isinstance(address, IPv6Address):
            ip = IPAddressV6(address=address, network=network.reference)

        ip_port = IPPort(address=ip.reference, protocol=tcp_protocol, port=port)
        yield ip_port

        service = Service(name=url.scheme)
        yield service

        ip_service = IPService(ip_port=ip_port.reference, service=service.reference)
        yield ip_service

        http_resource = None
        if hostname is not None:
            http_url = HostnameHTTPURL(
                network=network.reference,
                scheme=WebScheme(url.scheme),
                port=port,
                path=url.path,
                netloc=hostname.reference,
            )
            website = Website(hostname=hostname.reference, ip_service=ip_service.reference)
            yield website
            http_resource = HTTPResource(website=website.reference, web_url=http_url.reference)
            yield http_resource
        else:
            http_url = IPAddressHTTPURL(
                network=network.reference, scheme=WebScheme(url.scheme), port=port, path=url.path, netloc=url.netloc
            )

        if issue.getElementsByTagName("vulnerabilityClassifications"):
            vulnerability_classifications = issue.getElementsByTagName("vulnerabilityClassifications")[
                0
            ].firstChild.nodeValue

            soup = BeautifulSoup(vulnerability_classifications)
            for link_element in soup.find_all("a"):
                description = link_element.string.split(":")
                if description[0].startswith("CWE"):
                    finding_type = CWEFindingType(id=description[0])
                elif description[0].startswith("CAPEC"):
                    finding_type = CAPECFindingType(id=description[0])
                elif description[0].startswith("CVE"):
                    finding_type = CVEFindingType(id=description[0])
                else:
                    continue
                yield finding_type
                f = Finding(finding_type=finding_type.reference, ooi=http_url.reference, description=description[1])
                yield f

        if issue.getElementsByTagName("response"):
            response = issue.getElementsByTagName("response")[0]
            # decode the response if its encoded
            if response.attributes["base64"].value == "true":
                response = base64.b64decode(response.firstChild.nodeValue).decode()
            else:
                response = response.firstChild.nodeValue.decode()

            # currently we only support websites with hostnames as netloc, therefore we should only
            # add these headers if the resource exists
            if http_resource is not None:
                headers = response.split("\r\n\r\n")[0].split("\n\n")[0]
                for header in headers.splitlines():
                    header = header.split(":", 2)
                    # remove headers wihout key value structure
                    if len(header) == 2:
                        yield HTTPHeader(resource=http_resource.reference, key=header[0], value=header[1])
