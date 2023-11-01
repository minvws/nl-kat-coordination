from typing import Iterable, Union
from urllib.parse import urlparse

from haralyzer import HarParser

from boefjes.job_models import NormalizerMeta
from octopoes.models import OOI, Reference
from octopoes.models.ooi.web import CrawlInformation


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterable[OOI]:
    boefje_meta = normalizer_meta.raw_data.boefje_meta
    input_ooi = Reference.from_str(boefje_meta.input_ooi)

    har_parser = HarParser.from_string(raw)

    if len(har_parser.pages) != 1:
        raise Exception("Normalizer assumes there is only one page in the HAR")

    page = har_parser.pages[0]

    hostnames_and_cookies = {}

    for entry in page.entries:
        parsed_url = urlparse(entry.url)
        hostname = parsed_url.hostname
        if hostname not in hostnames_and_cookies:
            hostnames_and_cookies[hostname] = []
        for cookie in entry.response.raw_entry["cookies"]:
            if cookie not in hostnames_and_cookies[hostname]:
                hostnames_and_cookies[hostname].append(cookie)

    yield CrawlInformation(url=input_ooi, hostnames_and_cookies=hostnames_and_cookies)
