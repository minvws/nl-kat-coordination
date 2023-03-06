from octopoes.models.ooi.certificate import X509Certificate
from bits.expiring_certificate.expiring_certificate import run


def test_spf_discovery_simple_success():
    certificate = X509Certificate(
        subject="example.com",
        valid_from="2022-11-15T08:52:57",
        valid_until="2030-11-15T08:52:57",
        serial_number="abc123",
    )

    results = list(run(certificate, []))

    assert len(results) == 0


def test_spf_discovery_simple_expired():
    certificate = X509Certificate(
        subject="example.com",
        valid_from="2022-11-15T08:52:57",
        valid_until="2022-11-15T08:52:57",
        serial_number="abc123",
    )

    results = list(run(certificate, []))

    assert len(results) == 2
