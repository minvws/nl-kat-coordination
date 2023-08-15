from bits.cipher_classification.cipher_classification import run as cipher_classification

from octopoes.models.ooi.findings import Finding
from octopoes.models.ooi.network import IPAddressV4, IPPort
from octopoes.models.ooi.service import IPService, Service, TLSCipher


def test_recommendation_bad_ciphers():
    address = IPAddressV4(address="8.8.8.8", network="fake")
    port = IPPort(address=address.reference, protocol="tcp", port=22)
    ip_service = IPService(ip_port=port.reference, service=Service(name="https").reference)
    cipher = TLSCipher(
        ip_service=ip_service.reference,
        suites={
            "TLSv1.3": [
                {
                    "cipher_suite_alias": "TLS_AES_256_GCM_SHA384",
                    "encryption_algorithm": "AESGCM",
                    "cipher_suite_name": "TLS_AES_256_GCM_SHA384",
                    "bits": 253,
                    "key_size": 256,
                    "key_exchange_algorithm": "ECDH",
                    "cipher_suite_code": "x1302",
                },
                {
                    "cipher_suite_alias": "TLS_CHACHA20_POLY1305_SHA256",
                    "encryption_algorithm": "ChaCha20",
                    "cipher_suite_name": "TLS_CHACHA20_POLY1305_SHA256",
                    "bits": 253,
                    "key_size": 256,
                    "key_exchange_algorithm": "ECDH",
                    "cipher_suite_code": "x1303",
                },
                {
                    "cipher_suite_alias": "TLS_AES_128_GCM_SHA256",
                    "encryption_algorithm": "AESGCM",
                    "cipher_suite_name": "TLS_AES_128_GCM_SHA256",
                    "bits": 253,
                    "key_size": 128,
                    "key_exchange_algorithm": "ECDH",
                    "cipher_suite_code": "x1301",
                },
            ],
            "TLSv1.2": [
                {
                    "cipher_suite_alias": "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
                    "encryption_algorithm": "AESGCM",
                    "cipher_suite_name": "ECDHE-RSA-AES256-GCM-SHA384",
                    "bits": 521,
                    "key_size": 256,
                    "key_exchange_algorithm": "ECDH",
                    "cipher_suite_code": "xc030",
                },
                {
                    "cipher_suite_alias": "TLS_DHE_RSA_WITH_AES_256_GCM_SHA384",
                    "encryption_algorithm": "AESGCM",
                    "cipher_suite_name": "DHE-RSA-AES256-GCM-SHA384",
                    "bits": 2048,
                    "key_size": 256,
                    "key_exchange_algorithm": "DH",
                    "cipher_suite_code": "x9f",
                },
                {
                    "cipher_suite_alias": "TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256",
                    "encryption_algorithm": "ChaCha20",
                    "cipher_suite_name": "ECDHE-RSA-CHACHA20-POLY1305",
                    "bits": 521,
                    "key_size": 256,
                    "key_exchange_algorithm": "ECDH",
                    "cipher_suite_code": "xcca8",
                },
                {
                    "cipher_suite_alias": "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256",
                    "encryption_algorithm": "AESGCM",
                    "cipher_suite_name": "ECDHE-RSA-AES128-GCM-SHA256",
                    "bits": 521,
                    "key_size": 128,
                    "key_exchange_algorithm": "ECDH",
                    "cipher_suite_code": "xc02f",
                },
                {
                    "cipher_suite_alias": "TLS_DHE_RSA_WITH_AES_128_GCM_SHA256",
                    "encryption_algorithm": "AESGCM",
                    "cipher_suite_name": "DHE-RSA-AES128-GCM-SHA256",
                    "bits": 2048,
                    "key_size": 128,
                    "key_exchange_algorithm": "DH",
                    "cipher_suite_code": "x9e",
                },
            ],
        },
    )

    results = list(cipher_classification(cipher, {}, {}))

    assert len(results) == 2
    assert results[0].reference == "KATFindingType|KAT-RECOMMENDATION-BAD-CIPHER"
    finding = results[-1]
    assert isinstance(finding, Finding)
    assert (
        finding.description
        == "One or more of the cipher suites should not be used because:\nECDHE-RSA-AES256-GCM-SHA384 - "
        "TLSv1.2 protocol detected (Recommendation).\nDHE-RSA-AES256-GCM-SHA384 - TLSv1.2 protocol detected "
        "(Recommendation).\nECDHE-RSA-CHACHA20-POLY1305 - TLSv1.2 protocol detected (Recommendation).\n"
        "ECDHE-RSA-AES128-GCM-SHA256 - TLSv1.2 protocol detected (Recommendation).\nDHE-RSA-AES128-GCM-SHA256 - "
        "TLSv1.2 protocol detected (Recommendation)."
    )


def test_good_ciphers():
    address = IPAddressV4(address="8.8.8.8", network="fake")
    port = IPPort(address=address.reference, protocol="tcp", port=22)
    ip_service = IPService(ip_port=port.reference, service=Service(name="https").reference)
    cipher = TLSCipher(
        ip_service=ip_service.reference,
        suites={
            "TLSv1.3": [
                {
                    "cipher_suite_alias": "TLS_AES_256_GCM_SHA384",
                    "encryption_algorithm": "AESGCM",
                    "cipher_suite_name": "TLS_AES_256_GCM_SHA384",
                    "bits": 253,
                    "key_size": 256,
                    "key_exchange_algorithm": "ECDH",
                    "cipher_suite_code": "x1302",
                }
            ]
        },
    )

    results = list(cipher_classification(cipher, {}, {}))

    assert len(results) == 0
