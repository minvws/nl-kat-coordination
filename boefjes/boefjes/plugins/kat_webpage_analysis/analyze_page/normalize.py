import json
from collections.abc import Iterable

from Wappalyzer import Wappalyzer, WebPage

from boefjes.job_models import NormalizerMeta
from octopoes.models import OOI, Reference
from octopoes.models.ooi.software import Software, SoftwareInstance


def run(normalizer_meta: NormalizerMeta, raw: bytes | str) -> Iterable[OOI]:
    raw_respsone, body = raw.decode().split("\n\n", 1)
    response_object = json.loads(raw_respsone)
    url = response_object["response"]["url"]

    headers = json.loads(raw_respsone)

    wappalyzer = Wappalyzer.latest()
    web_page = WebPage(url, body, headers)
    results = wappalyzer.analyze_with_versions_and_categories(web_page)

    for name, data in results.items():
        software = Software(name=name, version=data["versions"].pop(0))
        software_instance = SoftwareInstance(ooi=Reference.from_str(url), software=software.reference)
        yield from [software, software_instance]
