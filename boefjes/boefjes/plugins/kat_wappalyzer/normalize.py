import json
from collections.abc import Iterable

from Wappalyzer import Wappalyzer, WebPage

from boefjes.job_models import NormalizerOutput
from octopoes.models import Reference
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.network import Network
from octopoes.models.ooi.software import Software, SoftwareInstance
from octopoes.models.ooi.web import HostnameHTTPURL


def run(input_ooi: dict, raw: bytes) -> Iterable[NormalizerOutput]:
    pk = input_ooi["primary_key"]
    tokenized_weburl = Reference.from_str(pk).tokenized["web_url"]
    tokenized_hostname = Reference.from_str(pk).tokenized["website"]["hostname"]

    network = Network(name=tokenized_hostname["network"]["name"])
    hostname = Hostname(network=network.reference, name=tokenized_hostname["name"])
    web_url = HostnameHTTPURL(
        network=network.reference,
        netloc=hostname.reference,
        port=tokenized_weburl["port"],
        scheme=tokenized_weburl["scheme"],
        path=tokenized_weburl["path"],
    )
    raw_respsone, raw_body = raw.split(b"\n\n", 1)
    response_object = json.loads(raw_respsone)
    url = response_object["response"]["url"]

    headers = response_object["response"]["headers"]
    body = raw_body.decode(response_object.get("encoding") or "utf-8", "replace")

    wappalyzer = Wappalyzer.latest()
    web_page = WebPage(url, body, headers)
    results = wappalyzer.analyze_with_versions_and_categories(web_page)

    for name, data in results.items():
        software = Software(name=name, version=data["versions"].pop(0) if data["versions"] else None)
        software_instance = SoftwareInstance(ooi=web_url.reference, software=software.reference)
        yield from [software, software_instance]
