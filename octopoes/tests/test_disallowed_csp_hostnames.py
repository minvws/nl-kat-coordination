from bits.disallowed_csp_hostnames.disallowed_csp_hostnames import run

from octopoes.models import Reference
from octopoes.models.ooi.web import HTTPHeaderHostname


def test_disallowed_csp_headers_no_findings():
    http_header_hostname = HTTPHeaderHostname(
        hostname=Reference.from_str("Hostname|internet|example.com"),
        header=Reference.from_str(
            "HTTPHeader|internet|1.1.1.1|tcp|443|https|internet|example.com|https|internet|example.com|443||Content-Security-Policy"
        ),
    )

    results = list(run(http_header_hostname, [], {}))

    assert results == []


def test_disallowed_csp_headers_simple_finding():
    http_header_hostname = HTTPHeaderHostname(
        hostname=Reference.from_str("Hostname|internet|bit.ly"),
        header=Reference.from_str(
            "HTTPHeader|internet|1.1.1.1|tcp|443|https|internet|example.com|https|internet|example.com|443||Content-Security-Policy"
        ),
    )

    results = list(run(http_header_hostname, [], {}))

    assert len(results) == 2


def test_disallowed_csp_headers_allow_url_shortener():
    http_header_hostname = HTTPHeaderHostname(
        hostname=Reference.from_str("Hostname|internet|bit.ly"),
        header=Reference.from_str(
            "HTTPHeader|internet|1.1.1.1|tcp|443|https|internet|example.com|https|internet|example.com|443||Content-Security-Policy"
        ),
    )

    results = list(run(http_header_hostname, [], {"disallow_url_shorteners": "false"}))

    assert results == []


def test_disallowed_csp_headers_disallow_custom_hostname():
    http_header_hostname = HTTPHeaderHostname(
        hostname=Reference.from_str("Hostname|internet|example.com"),
        header=Reference.from_str(
            "HTTPHeader|internet|1.1.1.1|tcp|443|https|internet|example.com|https|internet|example.com|443||Content-Security-Policy"
        ),
    )

    results = list(run(http_header_hostname, [], {"disallowed_hostnames": "example.com"}))

    assert len(results) == 2
