from bits.definitions import BitDefinition, BitParameterDefinition
from octopoes.models.ooi.certificate import (
    SubjectAlternativeNameHostname,
    SubjectAlternativeNameQualifier,
    X509Certificate,
)
from octopoes.models.ooi.web import Website

BIT = BitDefinition(
    id="ssl-certificate-hostname",
    consumes=X509Certificate,
    parameters=[
        BitParameterDefinition(ooi_type=Website, relation_path="certificate"),
        BitParameterDefinition(ooi_type=SubjectAlternativeNameHostname, relation_path="certificate"),
        BitParameterDefinition(ooi_type=SubjectAlternativeNameQualifier, relation_path="certificate"),
    ],
    module="bits.ssl_certificate_hostname.ssl_certificate_hostname",
)
