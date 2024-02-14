from collections.abc import Iterable
from urllib.parse import urljoin

import validators
from bs4 import BeautifulSoup

from boefjes.job_models import NormalizerMeta
from octopoes.models import OOI
from octopoes.models.ooi.network import Network
from octopoes.models.ooi.web import URL


def run(normalizer_meta: NormalizerMeta, raw: bytes | str) -> Iterable[OOI]:
    soup = BeautifulSoup(raw, "html.parser")
    images = set([img["src"] for img in soup.find_all("img", src=True)])

    network_name = normalizer_meta.raw_data.boefje_meta.arguments["input"]["website"]["hostname"]["network"]["name"]
    host = normalizer_meta.raw_data.boefje_meta.arguments["input"]["website"]["hostname"]["name"]
    service = normalizer_meta.raw_data.boefje_meta.arguments["input"]["website"]["ip_service"]["service"]["name"]

    url = f"{service}://{host}/"

    for img in images:
        if not validators.url(img):
            img = urljoin(url, img)

        yield URL(
            network=Network(name=network_name).reference,
            raw=img,
        )
