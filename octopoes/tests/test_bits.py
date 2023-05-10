from bits.https_availability.https_availability import run as run_https_availability
from bits.oois_in_headers.oois_in_headers import run as run_oois_in_headers

from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.findings import Finding
from octopoes.models.ooi.network import IPAddressV4, IPPort, Network
from octopoes.models.ooi.service import IPService, Service
from octopoes.models.ooi.web import URL, HostnameHTTPURL, HTTPHeader, HTTPHeaderURL, HTTPResource, Website


def test_url_extracted_by_oois_in_headers_url():
    header = HTTPHeader(resource="", key="Location", value="https://www.example.com")

    results = list(run_oois_in_headers(header, [], {}))

    url = results[0]
    assert isinstance(url, URL)
    assert url.raw == "https://www.example.com"
    assert url.network == "Network|internet"

    http_header_url = results[1]
    assert isinstance(http_header_url, HTTPHeaderURL)
    assert http_header_url.header == header.reference
    assert http_header_url.url == url.reference


def test_url_extracted_by_oois_in_headers_relative_path():
    ip_port = IPPort(
        address=IPAddressV4(address="1.1.1.1", network=Network(name="internet").reference).reference,
        protocol="tcp",
        port=443,
    )
    ip_service = IPService(ip_port=ip_port.reference, service=Service(name="https").reference)
    netloc = Hostname(name="www.example.com", network=Network(name="internet").reference)
    website = Website(ip_service=ip_service.reference, hostname=netloc.reference)
    web_url = HostnameHTTPURL(
        netloc=netloc.reference, path="/", scheme="https", network=Network(name="internet").reference, port=443
    )
    resource = HTTPResource(website=website.reference, web_url=web_url.reference)

    header = HTTPHeader(resource=resource.reference, key="Location", value="script.php")

    results = list(run_oois_in_headers(header, [], {}))

    url = results[0]
    assert isinstance(url, URL)
    assert url.raw == "https://www.example.com/script.php"
    assert url.network == "Network|internet"

    http_header_url = results[1]
    assert isinstance(http_header_url, HTTPHeaderURL)
    assert http_header_url.header == header.reference
    assert http_header_url.url == url.reference


def test_finding_generated_when_443_not_open_and_80_is_open():
    port_80 = IPPort(address="fake", protocol="tcp", port=80)
    website = Website(ip_service="fake", hostname="fake")
    results = list(run_https_availability(None, [port_80, website], {}))
    finding = results[0]
    assert isinstance(finding, Finding)
    assert finding.description == "HTTP port is open, but HTTPS port is not open"
