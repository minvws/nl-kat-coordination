from typing import Iterable, Union

from boefjes.job_models import NormalizerMeta
from octopoes.models import OOI, Reference

import io

import mitmproxy
from mitmproxy.exceptions import FlowReadException


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterable[OOI]:
    boefje_meta = normalizer_meta.raw_data.boefje_meta
    Reference.from_str(boefje_meta.input_ooi)
    flowfile = io.BytesIO(raw)
    freader = mitmproxy.io.FlowReader(flowfile)
    data = {}
    try:
        for f in freader.stream():
            if f.type != "http":
                continue
        host = f.request.host
        if not host in data:
            data[host] = set()
        for c in f.request.cookies:
            data[host].add(c)
            if f.response:
                for c in f.response.cookies.items():
                    data[host].add(c[0])
    except FlowReadException as e:
        print("Flow file corrupted: {}".format(e))