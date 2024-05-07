from bits.check_csp_header.check_csp_header import run

from octopoes.models.ooi.web import HTTPHeader


def test_https_hsts(http_resource_https):
    results = [
        list(run(HTTPHeader(resource=http_resource_https.reference, key=key, value=value), [], {}))
        for key, value in [
            ("Content-Type", "text/html"),
            ("Content-security-poliCY", "text/html"),
            ("content-security-policy", "http://abc.com"),
            ("content-security-policy", "https://abc.com"),
            ("content-security-policy", "https://*.com"),
            ("content-security-policy", "https://a.com; ...; media-src 'self'; media-src 10.10.10.10;"),
            ("content-security-policy", "unsafe-inline-uri * strict-dynamic; test http: 127.0.0.1"),
        ]
    ]

    assert results[0] == []
    assert len(results[1]) == 2
    assert results[1][0].id == "KAT-CSP-VULNERABILITIES"
    assert (
        results[1][1].description
        == """List of CSP findings:
 1. frame-src has not been defined or does not have a fallback.
 2. script-src has not been defined or does not have a fallback.
 3. base-uri has not been defined, default-src does not apply.
 4. frame-ancestors has not been defined.
 5. default-src has not been defined.
 6. CSP setting has no value."""
    )

    assert results[2][0].id == "KAT-CSP-VULNERABILITIES"
    assert (
        results[2][1].description
        == """List of CSP findings:
 1. Http should not be used in the CSP settings of an HTTP Header.
 2. frame-src has not been defined or does not have a fallback.
 3. script-src has not been defined or does not have a fallback.
 4. base-uri has not been defined, default-src does not apply.
 5. frame-ancestors has not been defined.
 6. default-src has not been defined.
 7. CSP setting has no value."""
    )

    assert results[3][0].id == "KAT-CSP-VULNERABILITIES"
    assert (
        results[3][1].description
        == """List of CSP findings:
 1. frame-src has not been defined or does not have a fallback.
 2. script-src has not been defined or does not have a fallback.
 3. base-uri has not been defined, default-src does not apply.
 4. frame-ancestors has not been defined.
 5. default-src has not been defined.
 6. CSP setting has no value."""
    )

    assert results[4][0].id == "KAT-CSP-VULNERABILITIES"
    assert (
        results[4][1].description
        == """List of CSP findings:
 1. The wildcard * for the scheme and host part of any URL should never be used in CSP settings.
 2. frame-src has not been defined or does not have a fallback.
 3. script-src has not been defined or does not have a fallback.
 4. base-uri has not been defined, default-src does not apply.
 5. frame-ancestors has not been defined.
 6. default-src has not been defined.
 7. CSP setting has no value."""
    )

    assert results[5][0].id == "KAT-CSP-VULNERABILITIES"
    assert (
        results[5][1].description
        == """List of CSP findings:
 1. frame-src has not been defined or does not have a fallback.
 2. script-src has not been defined or does not have a fallback.
 3. base-uri has not been defined, default-src does not apply.
 4. frame-ancestors has not been defined.
 5. default-src has not been defined.
 6. CSP setting has no value.
 7. CSP setting has no value.
 8. Private, local, reserved, multicast, loopback ips should not be allowed in the CSP settings.
 9. CSP setting has no value."""
    )

    assert results[6][0].id == "KAT-CSP-VULNERABILITIES"
    assert (
        results[6][1].description
        == """List of CSP findings:
 1. unsafe-inline, unsafe-eval and unsafe-hashes should not be used in the CSP settings of an HTTP Header.
 2. frame-src has not been defined or does not have a fallback.
 3. script-src has not been defined or does not have a fallback.
 4. base-uri has not been defined, default-src does not apply.
 5. frame-ancestors has not been defined.
 6. default-src has not been defined.
 7. unsafe-inline-uri has illogical values.
 8. A wildcard source should not be used in the value of any type in the CSP settings.
 9. a blanket protocol source should not be used in the value of any type in the CSP settings.
 10. Private, local, reserved, multicast, loopback ips should not be allowed in the CSP settings."""
    )
