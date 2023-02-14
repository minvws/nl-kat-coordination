from pathlib import Path

from tools.add_ooi_information import retirejs_info, cve_info, snyk_info, port_info, service_info, cwe_info, get_info


def test_retirejs_info():
    output = retirejs_info("RetireJS-jquerymobile-4738")
    output.pop("information updated")  # Remove timestamp

    assert output == {
        "description": "No summary available. Find more information at: "
        "http://osvdb.org/show/osvdb/94563, "
        "http://osvdb.org/show/osvdb/94562, "
        "http://osvdb.org/show/osvdb/94316, "
        "http://osvdb.org/show/osvdb/94561 or "
        "http://osvdb.org/show/osvdb/94560",
        "severity": "high",
        "source": "https://github.com/RetireJS/retire.js/blob/master/repository/jsrepository.json",
    }


def test_cve(mocker):
    CVESearch = mocker.patch("tools.add_ooi_information.CVESearch")

    summary = "The Discovery Service (casdscvc) in CA ARCserve Backup 12.0.5454.0 and earlier allows remote "
    "attackers to cause a denial of service (crash) via a packet with a large integer value used in "
    "an increment to TCP port 41523, which triggers a buffer over-read."
    CVESearch().id.return_value = {"summary": summary, "cvss": 5.0}
    output = cve_info("CVE-2008-1979")
    output.pop("information updated")  # Remove timestamp

    assert output == {
        "description": summary,
        "cvss": 5.0,
        "source": "https://cve.circl.lu/cve/CVE-2008-1979",
    }

    CVESearch().id.return_value = {}
    assert cve_info("CVE-none") == {"description": "Not found"}


def test_snyk_info(mocker):
    requests_patch = mocker.patch("tools.add_ooi_information.requests")
    requests_patch.get().content = (Path(__file__).parent / "stubs" / "snyk_response.html").read_bytes()

    output = snyk_info("SNYK-PYTHON-MECHANIZE-3232926")
    output.pop("information updated")  # Remove timestamp

    assert output == {
        "affected versions": "[,0.4.6)",
        "description": "Affected versions of this package are vulnerable to Regular "
        "Expression Denial of Service (ReDoS) due to insecure usage of "
        "regular expression in the compile method used in the "
        "AbstractBasicAuthHandler class. Exploiting this vulnerability "
        "is possible when parsing a malformed auth header.",
        "risk": "7.5",
        "source": "https://snyk.io/vuln/SNYK-PYTHON-MECHANIZE-3232926",
    }


def test_port_info(mocker):
    requests_patch = mocker.patch("tools.add_ooi_information.requests")
    requests_patch.get().text = (Path(__file__).parent / "stubs" / "wiki.html").read_text()

    descriptions, source = port_info("80", "TCP")

    assert descriptions == (
        "Hypertext Transfer Protocol (HTTP)[48][49] uses TCP in versions 1.x and 2. "
        "HTTP/3 uses QUIC,[50] a transport protocol on top of UDP."
    )
    assert source == "https://en.wikipedia.org/wiki/List_of_TCP_and_UDP_port_numbers"

    descriptions, source = port_info("443", "UDP")
    assert descriptions == (
        "Hypertext Transfer Protocol Secure (HTTPS)[48][49] uses TCP in versions 1.x "
        "and 2. HTTP/3 uses QUIC,[50] a transport protocol on top of UDP."
    )


def test_service_info(mocker):
    requests_patch = mocker.patch("tools.add_ooi_information.requests")
    requests_patch.get().text = (Path(__file__).parent / "stubs" / "iana_service.html").read_text()

    description, source = service_info("ssh")

    assert (
        description == "Service is usually on port 22, with protocol tcp: The Secure Shell (SSH) Protocol. "
        "Service is usually on port 22, with protocol udp: The Secure Shell (SSH) Protocol. "
        "Service is usually on port 22, with protocol sctp: SSH. Service is usually on port None, "
        "with protocol tcp: SSH Remote Login Protocol"
    )

    assert source == "https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml"

    output = get_info("Service", "ssh")
    output.pop("information updated")  # Remove timestamp

    assert output == {
        "description": description,
        "source": source,
    }


def test_cwe_info():
    output = cwe_info("CWE-20")
    output.pop("information updated")  # Remove timestamp

    assert output == {
        "description": "The product does not validate or incorrectly validates input "
        "that can affect the control flow or data flow of a program.",
        "source": "https://cwe.mitre.org/index.html",
    }

    output = cwe_info("CWE-223230")
    assert output == {"description": "Not found"}
