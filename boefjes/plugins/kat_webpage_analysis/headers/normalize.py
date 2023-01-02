import json
from typing import Union, Iterator
from octopoes.models import OOI, Reference
from octopoes.models.ooi.web import HTTPHeader

from boefjes.job_models import NormalizerMeta


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterator[OOI]:

    # fetch a reference to the original resource where these headers where downloaded from
    resource = Reference.from_str(normalizer_meta.raw_data.boefje_meta.input_ooi)

    # walk over the raw http header data, and split on newlines
    for header in raw.split("\n"):
        # for each line split on : to split the header-type from the header-value
        header = header.split(":")
        # yeild (one by one) the results as
        yield HTTPHeader(
            resource=resource,  # the original resource we found these headers on
            key=header[0],  # the header type
            value=header[1],
        )  # the header value
