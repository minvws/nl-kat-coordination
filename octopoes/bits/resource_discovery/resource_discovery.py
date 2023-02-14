from typing import List, Iterator, Union

from octopoes.models import OOI
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.web import Website, HostnameHTTPURL, HTTPResource


def run(
    hostname: Hostname,
    additional_oois: List[Union[HostnameHTTPURL, Website]],
) -> Iterator[OOI]:

    hostname_http_urls = [
        hostname_http_url for hostname_http_url in additional_oois if isinstance(hostname_http_url, HostnameHTTPURL)
    ]
    websites = [website for website in additional_oois if isinstance(website, Website)]

    # HTTPResource is cartesian product of HostnameHTTPURL and Websites
    for hostname_http_url in hostname_http_urls:
        for website in websites:

            # only create resource if ports are the same and schemes are the same
            if (
                int(website.ip_service.tokenized.ip_port.port) == hostname_http_url.port
                and website.ip_service.tokenized.service.name == hostname_http_url.scheme.value
            ):
                yield HTTPResource(
                    website=website.reference,
                    web_url=hostname_http_url.reference,
                )
