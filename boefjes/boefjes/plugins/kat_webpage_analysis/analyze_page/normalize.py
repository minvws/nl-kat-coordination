import json
from collections.abc import Iterable

from Wappalyzer import Wappalyzer, WebPage

from boefjes.job_models import NormalizerMeta
from octopoes.models import OOI, Reference
from octopoes.models.ooi.software import Software, SoftwareInstance


def run(normalizer_meta: NormalizerMeta, raw: bytes | str) -> Iterable[OOI]:
    # fetch a reference to the original resource where these headers where downloaded from
    web_url = normalizer_meta.raw_data.boefje_meta.arguments["input"]["web_url"]
    url = f"{web_url['scheme']}://{web_url['netloc']['name']}:{web_url['port']}{web_url['path']}"
    raw_headers, body = raw.decode().split("\n\n", 1)

    headers = json.loads(raw_headers)

    wappalyzer = Wappalyzer.latest()
    web_page = WebPage(url, body, headers)
    results = wappalyzer.analyze_with_versions_and_categories(web_page)

    for name, data in results.items():
        software = Software(name=name, version=data["versions"].pop(0))
        software_instance = SoftwareInstance(ooi=Reference.from_str(url), software=software.reference)
        yield from [software, software_instance]
