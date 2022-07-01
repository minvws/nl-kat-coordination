import re
from typing import Union, Iterator, List

import cryptography
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from octopoes.models import OOI, Reference
from octopoes.models.ooi.certificate import Certificate, AlgorithmType

from job import NormalizerMeta


def find_between(s: str, first: str, last: str) -> str:
    try:
        start = s.index(first) + len(first)
        end = s.index(last, start)
        return s[start:end]
    except ValueError:
        return ""


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterator[OOI]:
    # only get the first part of certificates
    contents = find_between(raw.decode(), "Certificate chain", "Certificate chain")

    if not contents:
        return

    input_ooi = normalizer_meta.boefje_meta.input_ooi

    # extract all certificates
    certificates = read_certificates(contents, Reference.from_str(input_ooi))

    # connect to website
    website_reference = Reference.from_str(input_ooi)

    # server certificate
    certificates[0].website = website_reference

    # chain certificates together
    last_certificate = None
    for certificate in reversed(certificates):
        if last_certificate is not None:
            certificate.signed_by = last_certificate.reference

        last_certificate = certificate
        yield certificate


def read_certificates(contents: str, website_reference: Reference) -> List[Certificate]:
    # iterate through the PEM certificates and decode them
    certificates = []
    for m in re.finditer(
        r"(?<=-----BEGIN CERTIFICATE-----).*?(?=-----END CERTIFICATE-----)",
        contents,
        flags=re.DOTALL,
    ):
        pem_contents = (
            "-----BEGIN CERTIFICATE-----" + m.group() + "-----END CERTIFICATE-----"
        )

        cert = x509.load_pem_x509_certificate(pem_contents.encode(), default_backend())
        subject = cert.subject.get_attributes_for_oid(x509.OID_COMMON_NAME)[0].value
        issuer = cert.issuer.get_attributes_for_oid(x509.OID_ORGANIZATION_NAME)[0].value
        valid_from = cert.not_valid_before.isoformat()
        valid_until = cert.not_valid_after.isoformat()
        pk_algorithm = ""
        pk_size = cert.public_key().key_size
        pk_number = (
            cert.public_key().public_numbers().n.to_bytes(pk_size // 8, "big").hex()
        )
        if isinstance(
            cert.public_key(),
            cryptography.hazmat.backends.openssl.x509.rsa.RSAPublicKey,
        ):
            pk_algorithm = str(AlgorithmType.RSA)

        certificate = Certificate(
            subject=subject,
            issuer=issuer,
            valid_from=valid_from,
            valid_until=valid_until,
            pk_algorithm=pk_algorithm,
            pk_size=pk_size,
            pk_number=pk_number,
            website=website_reference,
            signed_by=None,
        )
        # todo: alt names
        certificates.append(certificate)

    return certificates
