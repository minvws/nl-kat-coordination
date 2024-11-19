import json
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path

from tanimachi import Categories, Fingerprints, Groups, Har, Wappalyzer
from tanimachi.schemas import Entry, Log
from tanimachi.schemas.har import (
    Cache,
    Content,
    Cookie,
    Creator,
    Header,
    Request,
    Response,
    Timings,
)

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
    # raw_respsone, raw_body = raw.split(b"\n\n", 1)
    # response_object = json.loads(raw_respsone)
    # url = response_object["response"]["url"]
    #
    # headers = response_object["response"]["headers"]
    # body = raw_body.decode(response_object.get("encoding") or "utf-8", "replace")

    # with Path(__file__).parent.joinpath("technologies.json").open() as f:
    #     data = json.load(f)
    # wappalyzer = Wappalyzer(categories=data["categories"], technologies=data["technologies"])
    # web_page = WebPage(url, body, headers)
    #
    # results = asyncio.run(wappalyzer.analyze_with_versions_and_categories(web_page))

    fingerprints = Fingerprints.model_validate_pattern(
        Path(__file__).parent.joinpath("data/technologies/*.json").as_posix()
    )
    categories = Categories.model_validate_file(
        Path(__file__).parent.joinpath("data/categories.json")
    )
    groups = Groups.model_validate_file(
        Path(__file__).parent.joinpath("data/groups.json")
    )
    # har = Har.model_validate_file(
    #     "/Users/ammar/Downloads/tanimachi/tests/fixtures/har/example.har"
    # )
    #

    # create a Har model based on the response object
    har = Har.model_validate_json(raw)

    wappalyzer = Wappalyzer(fingerprints, categories=categories, groups=groups)
    detections = wappalyzer.analyze(har)

    for detection in detections:
        cpe = detection.fingerprint.cpe
        version = cpe.split(":")[1] if cpe else None
        software = Software(name=detection.fingerprint.id, version=version, cpe=cpe)
        software_instance = SoftwareInstance(
            ooi=web_url.reference, software=software.reference
        )
        yield from [software, software_instance]
